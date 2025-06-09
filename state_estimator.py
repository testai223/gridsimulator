"""Simple State Estimator implementation for power systems using Weighted Least Squares."""

import numpy as np
import pandas as pd
import pandapower as pp
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import random


class MeasurementType(Enum):
    """Types of measurements in the power system."""
    VOLTAGE_MAGNITUDE = "vm"
    ACTIVE_POWER_INJECTION = "p_inj"
    REACTIVE_POWER_INJECTION = "q_inj"
    ACTIVE_POWER_FLOW = "p_flow"
    REACTIVE_POWER_FLOW = "q_flow"


@dataclass
class Measurement:
    """Represents a single measurement in the power system."""
    meas_type: MeasurementType
    bus_from: int
    bus_to: Optional[int]  # None for injection measurements
    value: float
    variance: float
    element_idx: Optional[int] = None  # Index in line/trafo table


class StateEstimator:
    """Simple Weighted Least Squares state estimator for power systems."""
    
    def __init__(self, network: pp.pandapowerNet):
        """Initialize state estimator with pandapower network."""
        import copy
        self.net = copy.deepcopy(network)
        self.measurements: List[Measurement] = []
        self.state_vector: Optional[np.ndarray] = None
        self.covariance_matrix: Optional[np.ndarray] = None
        self.jacobian: Optional[np.ndarray] = None
        
        # Run power flow to get true values
        try:
            pp.runpp(self.net, verbose=False, numba=False)
        except pp.LoadflowNotConverged:
            print("Warning: Power flow did not converge for true system state")
    
    def add_voltage_measurements(self, buses: List[int], noise_std: float = 0.01):
        """Add voltage magnitude measurements at specified buses."""
        for bus in buses:
            if bus in self.net.res_bus.index:
                true_value = self.net.res_bus.loc[bus, 'vm_pu']
                measured_value = true_value + random.gauss(0, noise_std)
                
                measurement = Measurement(
                    meas_type=MeasurementType.VOLTAGE_MAGNITUDE,
                    bus_from=bus,
                    bus_to=None,
                    value=measured_value,
                    variance=noise_std**2
                )
                self.measurements.append(measurement)
    
    def add_power_injection_measurements(self, buses: List[int], noise_std: float = 0.02):
        """Add active and reactive power injection measurements."""
        for bus in buses:
            if bus in self.net.res_bus.index:
                # Active power injection
                true_p = self.net.res_bus.loc[bus, 'p_mw']
                measured_p = true_p + random.gauss(0, noise_std * abs(true_p) if true_p != 0 else noise_std)
                
                p_measurement = Measurement(
                    meas_type=MeasurementType.ACTIVE_POWER_INJECTION,
                    bus_from=bus,
                    bus_to=None,
                    value=measured_p,
                    variance=(noise_std * abs(true_p) if true_p != 0 else noise_std)**2
                )
                self.measurements.append(p_measurement)
                
                # Reactive power injection
                true_q = self.net.res_bus.loc[bus, 'q_mvar']
                measured_q = true_q + random.gauss(0, noise_std * abs(true_q) if true_q != 0 else noise_std)
                
                q_measurement = Measurement(
                    meas_type=MeasurementType.REACTIVE_POWER_INJECTION,
                    bus_from=bus,
                    bus_to=None,
                    value=measured_q,
                    variance=(noise_std * abs(true_q) if true_q != 0 else noise_std)**2
                )
                self.measurements.append(q_measurement)
    
    def add_power_flow_measurements(self, lines: List[int], noise_std: float = 0.02):
        """Add active and reactive power flow measurements on lines."""
        for line_idx in lines:
            if line_idx in self.net.res_line.index:
                bus_from = self.net.line.loc[line_idx, 'from_bus']
                bus_to = self.net.line.loc[line_idx, 'to_bus']
                
                # Active power flow (from side)
                true_p = self.net.res_line.loc[line_idx, 'p_from_mw']
                measured_p = true_p + random.gauss(0, noise_std * abs(true_p) if true_p != 0 else noise_std)
                
                p_measurement = Measurement(
                    meas_type=MeasurementType.ACTIVE_POWER_FLOW,
                    bus_from=bus_from,
                    bus_to=bus_to,
                    value=measured_p,
                    variance=(noise_std * abs(true_p) if true_p != 0 else noise_std)**2,
                    element_idx=line_idx
                )
                self.measurements.append(p_measurement)
                
                # Reactive power flow (from side)
                true_q = self.net.res_line.loc[line_idx, 'q_from_mvar']
                measured_q = true_q + random.gauss(0, noise_std * abs(true_q) if true_q != 0 else noise_std)
                
                q_measurement = Measurement(
                    meas_type=MeasurementType.REACTIVE_POWER_FLOW,
                    bus_from=bus_from,
                    bus_to=bus_to,
                    value=measured_q,
                    variance=(noise_std * abs(true_q) if true_q != 0 else noise_std)**2,
                    element_idx=line_idx
                )
                self.measurements.append(q_measurement)
    
    def create_measurement_set_ieee9(self, simple_mode=True):
        """Create a measurement set for IEEE 9-bus system."""
        if simple_mode:
            # Simple case: only voltage measurements for debugging
            voltage_buses = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # All buses
            self.add_voltage_measurements(voltage_buses, noise_std=0.01)
            print(f"Created {len(self.measurements)} voltage measurements for IEEE 9-bus system")
        else:
            # Comprehensive measurement set
            voltage_buses = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # All buses
            self.add_voltage_measurements(voltage_buses, noise_std=0.005)
            
            # Power injection measurements at key buses
            injection_buses = [4, 5, 8]  # Load buses only
            self.add_power_injection_measurements(injection_buses, noise_std=0.02)
            
            # Power flow measurements on a few critical lines
            flow_lines = [0, 2, 4]  # Selected transmission lines
            self.add_power_flow_measurements(flow_lines, noise_std=0.03)
            
            print(f"Created {len(self.measurements)} measurements for IEEE 9-bus system")
    
    def _build_measurement_vector(self) -> np.ndarray:
        """Build measurement vector z from all measurements."""
        return np.array([m.value for m in self.measurements])
    
    def _build_weight_matrix(self) -> np.ndarray:
        """Build weight matrix W (inverse of measurement covariance matrix)."""
        variances = np.array([m.variance for m in self.measurements])
        return np.diag(1.0 / variances)
    
    def _calculate_measurement_functions(self, voltage_magnitudes: np.ndarray, 
                                       voltage_angles: np.ndarray) -> np.ndarray:
        """Calculate measurement functions h(x) for given state."""
        h = np.zeros(len(self.measurements))
        
        # Build admittance matrix for more accurate calculations
        n_buses = len(self.net.bus)
        Y = np.zeros((n_buses, n_buses), dtype=complex)
        
        # Add line admittances
        for line_idx in self.net.line.index:
            from_bus = self.net.line.loc[line_idx, 'from_bus']
            to_bus = self.net.line.loc[line_idx, 'to_bus']
            
            r = self.net.line.loc[line_idx, 'r_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
            x = self.net.line.loc[line_idx, 'x_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
            
            if r**2 + x**2 > 0:
                y_line = 1.0 / (r + 1j * x)
                Y[from_bus, to_bus] -= y_line
                Y[to_bus, from_bus] -= y_line
                Y[from_bus, from_bus] += y_line
                Y[to_bus, to_bus] += y_line
        
        # Convert to complex voltages
        V = voltage_magnitudes * np.exp(1j * voltage_angles)
        
        for i, meas in enumerate(self.measurements):
            if meas.meas_type == MeasurementType.VOLTAGE_MAGNITUDE:
                h[i] = voltage_magnitudes[meas.bus_from]
            
            elif meas.meas_type == MeasurementType.ACTIVE_POWER_INJECTION:
                bus = meas.bus_from
                # P_inj = Re(V_i * conj(sum(Y_ij * V_j)))
                current_sum = sum(Y[bus, j] * V[j] for j in range(n_buses))
                power_complex = V[bus] * np.conj(current_sum)
                h[i] = power_complex.real
            
            elif meas.meas_type == MeasurementType.REACTIVE_POWER_INJECTION:
                bus = meas.bus_from
                # Q_inj = Im(V_i * conj(sum(Y_ij * V_j)))
                current_sum = sum(Y[bus, j] * V[j] for j in range(n_buses))
                power_complex = V[bus] * np.conj(current_sum)
                h[i] = power_complex.imag
            
            elif meas.meas_type == MeasurementType.ACTIVE_POWER_FLOW:
                bus_from = meas.bus_from
                bus_to = meas.bus_to
                line_idx = meas.element_idx
                
                r = self.net.line.loc[line_idx, 'r_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
                x = self.net.line.loc[line_idx, 'x_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
                
                if r**2 + x**2 > 0:
                    y_line = 1.0 / (r + 1j * x)
                    # P_flow = Re(V_from * conj((V_from - V_to) * y_line))
                    current = (V[bus_from] - V[bus_to]) * y_line
                    power_complex = V[bus_from] * np.conj(current)
                    h[i] = power_complex.real
                else:
                    h[i] = 0.0
            
            elif meas.meas_type == MeasurementType.REACTIVE_POWER_FLOW:
                bus_from = meas.bus_from
                bus_to = meas.bus_to
                line_idx = meas.element_idx
                
                r = self.net.line.loc[line_idx, 'r_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
                x = self.net.line.loc[line_idx, 'x_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
                
                if r**2 + x**2 > 0:
                    y_line = 1.0 / (r + 1j * x)
                    # Q_flow = Im(V_from * conj((V_from - V_to) * y_line))
                    current = (V[bus_from] - V[bus_to]) * y_line
                    power_complex = V[bus_from] * np.conj(current)
                    h[i] = power_complex.imag
                else:
                    h[i] = 0.0
        
        return h
    
    def _calculate_jacobian(self, voltage_magnitudes: np.ndarray, 
                          voltage_angles: np.ndarray) -> np.ndarray:
        """Calculate Jacobian matrix H for linearization."""
        n_meas = len(self.measurements)
        n_buses = len(self.net.bus)
        n_states = 2 * n_buses - 1  # angles (n-1) + magnitudes (n)
        
        H = np.zeros((n_meas, n_states))
        
        # For voltage measurements, Jacobian is trivial
        angle_col = 0
        mag_col = n_buses - 1
        
        for i, meas in enumerate(self.measurements):
            if meas.meas_type == MeasurementType.VOLTAGE_MAGNITUDE:
                # ∂|V_i|/∂|V_j| = δ_ij, ∂|V_i|/∂θ_j = 0
                H[i, mag_col + meas.bus_from] = 1.0
            
            else:
                # For power measurements, use numerical differentiation with smaller epsilon
                epsilon = 1e-8
                h_base = self._calculate_measurement_functions(voltage_magnitudes, voltage_angles)
                
                # Derivatives w.r.t voltage angles (skip slack bus)
                for j in range(1, n_buses):  # Skip slack bus (bus 0)
                    va_pert = voltage_angles.copy()
                    va_pert[j] += epsilon
                    h_pert = self._calculate_measurement_functions(voltage_magnitudes, va_pert)
                    H[i, j-1] = (h_pert[i] - h_base[i]) / epsilon
                
                # Derivatives w.r.t voltage magnitudes
                for j in range(n_buses):
                    vm_pert = voltage_magnitudes.copy()
                    vm_pert[j] += epsilon
                    h_pert = self._calculate_measurement_functions(vm_pert, voltage_angles)
                    H[i, mag_col + j] = (h_pert[i] - h_base[i]) / epsilon
        
        return H
    
    def estimate_state(self, max_iterations: int = 10, tolerance: float = 1e-4) -> Dict[str, Any]:
        """Perform state estimation using Weighted Least Squares."""
        if not self.measurements:
            raise ValueError("No measurements available for state estimation")
        
        # Initialize state vector with power flow results as starting point
        n_buses = len(self.net.bus)
        
        # Use power flow results as initial guess
        try:
            pp.runpp(self.net, verbose=False, numba=False)
            voltage_angles = np.zeros(n_buses)
            if 'va_degree' in self.net.res_bus.columns:
                voltage_angles = np.deg2rad(self.net.res_bus['va_degree'].values)
            voltage_magnitudes = self.net.res_bus['vm_pu'].values
        except:
            voltage_angles = np.zeros(n_buses)  # Start with flat voltage angles
            voltage_magnitudes = np.ones(n_buses)  # Start with flat voltage profile
        
        # Build measurement and weight matrices
        z = self._build_measurement_vector()
        W = self._build_weight_matrix()
        
        results = {
            'converged': False,
            'iterations': 0,
            'voltage_magnitudes': voltage_magnitudes.copy(),
            'voltage_angles': voltage_angles.copy(),
            'measurement_residuals': None,
            'objective_function': None
        }
        
        for iteration in range(max_iterations):
            # Calculate measurement functions and Jacobian
            h = self._calculate_measurement_functions(voltage_magnitudes, voltage_angles)
            H = self._calculate_jacobian(voltage_magnitudes, voltage_angles)
            
            # Calculate residuals
            residuals = z - h
            
            # Check convergence
            if np.linalg.norm(residuals) < tolerance:
                results['converged'] = True
                results['iterations'] = iteration + 1
                break
            
            # Solve normal equations: (H^T * W * H) * Δx = H^T * W * residuals
            try:
                HTW = H.T @ W
                HTWH = HTW @ H
                HTWr = HTW @ residuals
                
                # Add small regularization for numerical stability
                HTWH += np.eye(HTWH.shape[0]) * 1e-8
                
                delta_x = np.linalg.solve(HTWH, HTWr)
                
                # Update state vector
                n_angle_states = n_buses - 1
                voltage_angles[1:] += delta_x[:n_angle_states]  # Skip slack bus
                voltage_magnitudes += delta_x[n_angle_states:]
                
            except np.linalg.LinAlgError:
                print(f"Numerical error at iteration {iteration + 1}")
                break
        
        # Calculate final results
        h_final = self._calculate_measurement_functions(voltage_magnitudes, voltage_angles)
        final_residuals = z - h_final
        objective = final_residuals.T @ W @ final_residuals
        
        results.update({
            'voltage_magnitudes': voltage_magnitudes,
            'voltage_angles': voltage_angles,
            'measurement_residuals': final_residuals,
            'objective_function': objective,
            'measurements_count': len(self.measurements)
        })
        
        return results
    
    def get_measurement_summary(self) -> pd.DataFrame:
        """Get summary of all measurements."""
        data = []
        for i, meas in enumerate(self.measurements):
            data.append({
                'Index': i,
                'Type': meas.meas_type.value,
                'Bus From': meas.bus_from,
                'Bus To': meas.bus_to if meas.bus_to is not None else '-',
                'Value': f"{meas.value:.4f}",
                'Std Dev': f"{np.sqrt(meas.variance):.4f}",
                'Element': meas.element_idx if meas.element_idx is not None else '-'
            })
        
        return pd.DataFrame(data)
    
    def compare_with_true_state(self, estimated_results: Dict[str, Any]) -> pd.DataFrame:
        """Compare estimated state with true power flow results."""
        try:
            pp.runpp(self.net, verbose=False)
            
            data = []
            for bus in self.net.bus.index:
                true_vm = self.net.res_bus.loc[bus, 'vm_pu']
                true_va = np.rad2deg(self.net.res_bus.loc[bus, 'va_degree']) if 'va_degree' in self.net.res_bus.columns else 0.0
                
                est_vm = estimated_results['voltage_magnitudes'][bus]
                est_va = np.rad2deg(estimated_results['voltage_angles'][bus])
                
                data.append({
                    'Bus': bus,
                    'True V (pu)': f"{true_vm:.4f}",
                    'Est V (pu)': f"{est_vm:.4f}",
                    'V Error (%)': f"{100*(est_vm-true_vm)/true_vm:.2f}",
                    'True Angle (deg)': f"{true_va:.2f}",
                    'Est Angle (deg)': f"{est_va:.2f}",
                    'Angle Error (deg)': f"{est_va-true_va:.2f}"
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            print(f"Error comparing with true state: {e}")
            return pd.DataFrame()


def run_ieee9_state_estimation() -> Dict[str, Any]:
    """Run state estimation on IEEE 9-bus system."""
    from examples import create_ieee_9_bus
    
    # Create IEEE 9-bus system
    net = create_ieee_9_bus()
    
    # Initialize state estimator
    estimator = StateEstimator(net)
    
    # Create measurement set (simple mode for better convergence)
    estimator.create_measurement_set_ieee9(simple_mode=True)
    
    # Run state estimation
    results = estimator.estimate_state()
    
    # Print results
    print("\n" + "="*60)
    print("IEEE 9-Bus State Estimation Results")
    print("="*60)
    print(f"Converged: {results['converged']}")
    print(f"Iterations: {results['iterations']}")
    print(f"Measurements: {results['measurements_count']}")
    print(f"Objective function: {results['objective_function']:.6f}")
    
    # Show measurement summary
    print("\nMeasurement Summary:")
    print(estimator.get_measurement_summary().to_string(index=False))
    
    # Compare with true state
    print("\nComparison with True State:")
    comparison = estimator.compare_with_true_state(results)
    print(comparison.to_string(index=False))
    
    return {
        'estimator': estimator,
        'results': results,
        'comparison': comparison
    }


if __name__ == "__main__":
    # Run example
    run_ieee9_state_estimation()