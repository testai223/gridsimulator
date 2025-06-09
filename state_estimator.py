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
    
    def create_measurement_set_ieee9(self):
        """Create a comprehensive measurement set for IEEE 9-bus system."""
        # Voltage measurements at all buses except slack
        voltage_buses = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # All buses
        self.add_voltage_measurements(voltage_buses, noise_std=0.005)
        
        # Power injection measurements at load buses and generator buses
        injection_buses = [0, 1, 2, 4, 5, 8]  # Generator and load buses
        self.add_power_injection_measurements(injection_buses, noise_std=0.015)
        
        # Power flow measurements on critical lines
        flow_lines = [0, 1, 2, 3, 4, 5]  # All transmission lines
        self.add_power_flow_measurements(flow_lines, noise_std=0.02)
        
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
        
        for i, meas in enumerate(self.measurements):
            if meas.meas_type == MeasurementType.VOLTAGE_MAGNITUDE:
                h[i] = voltage_magnitudes[meas.bus_from]
            
            elif meas.meas_type == MeasurementType.ACTIVE_POWER_INJECTION:
                # Simplified active power injection calculation
                bus = meas.bus_from
                vm = voltage_magnitudes[bus]
                va = voltage_angles[bus]
                
                # Get connected buses via lines
                p_inj = 0.0
                for line_idx in self.net.line.index:
                    if self.net.line.loc[line_idx, 'from_bus'] == bus:
                        to_bus = self.net.line.loc[line_idx, 'to_bus']
                        vm_to = voltage_magnitudes[to_bus]
                        va_to = voltage_angles[to_bus]
                        
                        # Simple line model: P = (V1*V2/X) * sin(θ1-θ2)
                        x = self.net.line.loc[line_idx, 'x_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
                        if x > 0:
                            p_inj += (vm * vm_to / x) * np.sin(va - va_to)
                    
                    elif self.net.line.loc[line_idx, 'to_bus'] == bus:
                        from_bus = self.net.line.loc[line_idx, 'from_bus']
                        vm_from = voltage_magnitudes[from_bus]
                        va_from = voltage_angles[from_bus]
                        
                        x = self.net.line.loc[line_idx, 'x_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
                        if x > 0:
                            p_inj += (vm * vm_from / x) * np.sin(va - va_from)
                
                h[i] = p_inj
            
            elif meas.meas_type == MeasurementType.ACTIVE_POWER_FLOW:
                # Simplified power flow calculation
                bus_from = meas.bus_from
                bus_to = meas.bus_to
                vm_from = voltage_magnitudes[bus_from]
                vm_to = voltage_magnitudes[bus_to]
                va_from = voltage_angles[bus_from]
                va_to = voltage_angles[bus_to]
                
                # Simple line model
                line_idx = meas.element_idx
                x = self.net.line.loc[line_idx, 'x_ohm_per_km'] * self.net.line.loc[line_idx, 'length_km']
                if x > 0:
                    h[i] = (vm_from * vm_to / x) * np.sin(va_from - va_to)
                else:
                    h[i] = 0.0
            
            # For reactive power measurements, use simplified models
            elif meas.meas_type in [MeasurementType.REACTIVE_POWER_INJECTION, 
                                  MeasurementType.REACTIVE_POWER_FLOW]:
                h[i] = 0.0  # Simplified: assume zero reactive power
        
        return h
    
    def _calculate_jacobian(self, voltage_magnitudes: np.ndarray, 
                          voltage_angles: np.ndarray) -> np.ndarray:
        """Calculate Jacobian matrix H for linearization."""
        n_meas = len(self.measurements)
        n_buses = len(self.net.bus)
        n_states = 2 * n_buses - 1  # angles (n-1) + magnitudes (n)
        
        H = np.zeros((n_meas, n_states))
        
        # Simple numerical differentiation for Jacobian
        epsilon = 1e-6
        h_base = self._calculate_measurement_functions(voltage_magnitudes, voltage_angles)
        
        # Derivatives w.r.t voltage angles (first n-1 states, skip slack bus)
        for j in range(n_buses - 1):
            va_pert = voltage_angles.copy()
            va_pert[j+1] += epsilon  # Skip slack bus (bus 0)
            h_pert = self._calculate_measurement_functions(voltage_magnitudes, va_pert)
            H[:, j] = (h_pert - h_base) / epsilon
        
        # Derivatives w.r.t voltage magnitudes (last n states)
        for j in range(n_buses):
            vm_pert = voltage_magnitudes.copy()
            vm_pert[j] += epsilon
            h_pert = self._calculate_measurement_functions(vm_pert, voltage_angles)
            H[:, n_buses - 1 + j] = (h_pert - h_base) / epsilon
        
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
    
    # Create measurement set
    estimator.create_measurement_set_ieee9()
    
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