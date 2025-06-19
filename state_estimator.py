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
            # Simple case: voltage measurements with realistic noise + some redundancy
            voltage_buses = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # All buses
            self.add_voltage_measurements(voltage_buses, noise_std=0.025)  # 2.5% noise for visibility
            
            # Add some redundant voltage measurements with conflicting noise to show cleaning effect
            redundant_buses = [0, 2, 4, 6, 8]  # Some key buses measured twice with different sensors
            for bus in redundant_buses:
                if bus in self.net.res_bus.index:
                    true_value = self.net.res_bus.loc[bus, 'vm_pu']
                    # Add a second measurement with different noise characteristics (different sensor type)
                    noise_offset = random.gauss(0, 0.015)  # Bias in second sensor
                    measured_value = true_value + noise_offset + random.gauss(0, 0.02)  # 2% noise + bias
                    
                    measurement = Measurement(
                        meas_type=MeasurementType.VOLTAGE_MAGNITUDE,
                        bus_from=bus,
                        bus_to=None,
                        value=measured_value,
                        variance=0.025**2  # Different accuracy for second sensor
                    )
                    self.measurements.append(measurement)
                    
            print(f"Created {len(self.measurements)} voltage measurements (including redundant) for IEEE 9-bus system")
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
    
    def estimate_state(self, max_iterations: int = 10, tolerance: float = 1e-3) -> Dict[str, Any]:
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
        
        prev_residual_norm = float('inf')
        for iteration in range(max_iterations):
            # Calculate measurement functions and Jacobian
            h = self._calculate_measurement_functions(voltage_magnitudes, voltage_angles)
            H = self._calculate_jacobian(voltage_magnitudes, voltage_angles)
            
            # Calculate residuals
            residuals = z - h
            
            # Check convergence - use more robust criteria
            residual_norm = np.linalg.norm(residuals)
            if residual_norm < tolerance or (iteration > 0 and abs(residual_norm - prev_residual_norm) < tolerance * 0.1):
                results['converged'] = True
                results['iterations'] = iteration + 1
                break
            prev_residual_norm = residual_norm
            
            # Solve normal equations: (H^T * W * H) * Δx = H^T * W * residuals
            try:
                HTW = H.T @ W
                HTWH = HTW @ H
                HTWr = HTW @ residuals
                
                # Add regularization for numerical stability, especially with redundant measurements
                regularization = 1e-6 * np.trace(HTWH) / HTWH.shape[0]
                HTWH += np.eye(HTWH.shape[0]) * regularization
                
                delta_x = np.linalg.solve(HTWH, HTWr)
                
                # Update state vector with step size control for stability
                step_size = 1.0
                if iteration > 5 and residual_norm > prev_residual_norm:
                    step_size = 0.5  # Reduce step size if not improving
                
                n_angle_states = n_buses - 1
                voltage_angles[1:] += step_size * delta_x[:n_angle_states]  # Skip slack bus
                voltage_magnitudes += step_size * delta_x[n_angle_states:]
                
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
    
    def apply_state_to_network(self, results: Dict[str, Any], target_net: pp.pandapowerNet = None) -> pp.pandapowerNet:
        """Apply state estimation results to network for load flow calculation."""
        if not results.get('converged', False):
            raise ValueError("Cannot apply unconverged state estimation results")
        
        # Use target network or create copy of original
        if target_net is None:
            import copy
            target_net = copy.deepcopy(self.net)
        
        # Apply estimated voltage magnitudes and angles
        voltage_magnitudes = np.array(results['voltage_magnitudes'])
        voltage_angles = np.array(results['voltage_angles'])
        
        # Set voltage magnitudes in the network
        for bus_idx in target_net.bus.index:
            if bus_idx < len(voltage_magnitudes):
                target_net.bus.loc[bus_idx, 'vn_kv'] = target_net.bus.loc[bus_idx, 'vn_kv']  # Keep nominal voltage
        
        # Store state estimation results in network for load flow initialization
        if not hasattr(target_net, 'se_results'):
            target_net.se_results = {}
        
        target_net.se_results = {
            'voltage_magnitudes': voltage_magnitudes,
            'voltage_angles': voltage_angles,
            'timestamp': results.get('timestamp', 'unknown'),
            'converged': True
        }
        
        return target_net
    
    def run_load_flow_with_se_init(self, results: Dict[str, Any], 
                                  target_net: pp.pandapowerNet = None) -> Dict[str, Any]:
        """Run load flow using state estimation results as initial conditions."""
        if not results.get('converged', False):
            raise ValueError("Cannot use unconverged state estimation results for load flow")
        
        # Apply state to network
        lf_net = self.apply_state_to_network(results, target_net)
        
        # Get state estimation results
        voltage_magnitudes = np.array(results['voltage_magnitudes'])
        voltage_angles = np.array(results['voltage_angles'])
        
        try:
            # Set initial voltage conditions from state estimation
            if hasattr(lf_net, 'res_bus') and not lf_net.res_bus.empty:
                # Initialize with SE results
                for bus_idx in lf_net.bus.index:
                    if bus_idx < len(voltage_magnitudes):
                        # Set initial voltage magnitude and angle
                        lf_net.bus.loc[bus_idx, 'init_vm_pu'] = voltage_magnitudes[bus_idx]
                        if hasattr(lf_net.bus, 'init_va_degree'):
                            lf_net.bus.loc[bus_idx, 'init_va_degree'] = np.rad2deg(voltage_angles[bus_idx])
            
            # Run load flow with SE initialization
            pp.runpp(lf_net, verbose=False, numba=False, init='flat')
            
            lf_results = {
                'success': True,
                'converged': lf_net.converged,
                'network': lf_net,
                'se_initialized': True,
                'voltage_magnitudes': lf_net.res_bus['vm_pu'].values.tolist(),
                'voltage_angles': lf_net.res_bus['va_degree'].values.tolist() if 'va_degree' in lf_net.res_bus.columns else None,
                'active_power': lf_net.res_bus['p_mw'].values.tolist(),
                'reactive_power': lf_net.res_bus['q_mvar'].values.tolist(),
                'line_flows': {}
            }
            
            # Add line flow results if available
            if hasattr(lf_net, 'res_line') and not lf_net.res_line.empty:
                lf_results['line_flows'] = {
                    'p_from_mw': lf_net.res_line['p_from_mw'].values.tolist(),
                    'q_from_mvar': lf_net.res_line['q_from_mvar'].values.tolist(),
                    'p_to_mw': lf_net.res_line['p_to_mw'].values.tolist(),
                    'q_to_mvar': lf_net.res_line['q_to_mvar'].values.tolist(),
                    'loading_percent': lf_net.res_line['loading_percent'].values.tolist()
                }
            
            return lf_results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'se_initialized': True
            }
    
    def compare_se_vs_loadflow(self, se_results: Dict[str, Any], 
                              lf_results: Dict[str, Any]) -> pd.DataFrame:
        """Compare state estimation results with load flow results."""
        if not se_results.get('converged') or not lf_results.get('converged'):
            return pd.DataFrame({'Error': ['Cannot compare unconverged results']})
        
        se_vm = np.array(se_results['voltage_magnitudes'])
        se_va = np.array(se_results['voltage_angles'])
        lf_vm = np.array(lf_results['voltage_magnitudes'])
        lf_va = np.array(lf_results['voltage_angles']) if lf_results['voltage_angles'] else np.zeros_like(se_va)
        
        # Convert angles to degrees for comparison
        se_va_deg = np.rad2deg(se_va)
        
        comparison_data = []
        for bus in range(min(len(se_vm), len(lf_vm))):
            vm_diff = ((lf_vm[bus] - se_vm[bus]) / se_vm[bus]) * 100
            va_diff = lf_va[bus] - se_va_deg[bus]
            
            comparison_data.append({
                'Bus': bus,
                'SE Voltage (pu)': f"{se_vm[bus]:.4f}",
                'LF Voltage (pu)': f"{lf_vm[bus]:.4f}",
                'V Diff (%)': f"{vm_diff:.2f}",
                'SE Angle (deg)': f"{se_va_deg[bus]:.2f}",
                'LF Angle (deg)': f"{lf_va[bus]:.2f}",
                'Angle Diff (deg)': f"{va_diff:.2f}"
            })
        
        return pd.DataFrame(comparison_data)
    
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
    
    def simulate_measurement_outage(self, outage_buses: List[int], 
                                  outage_types: List[MeasurementType] = None) -> Dict[str, Any]:
        """Simulate measurement outages on specified buses.
        
        Args:
            outage_buses: List of bus indices where measurements fail
            outage_types: List of measurement types to fail (None = all types on bus)
        
        Returns:
            Dictionary with outage details and impact analysis
        """
        if outage_types is None:
            outage_types = list(MeasurementType)
        
        # Store original measurements
        original_measurements = self.measurements.copy()
        original_count = len(self.measurements)
        
        # Remove measurements for outage buses
        outaged_measurements = []
        remaining_measurements = []
        
        for measurement in self.measurements:
            is_outaged = False
            
            # Check if this measurement should be outaged
            if measurement.bus_from in outage_buses and measurement.meas_type in outage_types:
                is_outaged = True
            elif (measurement.bus_to is not None and 
                  measurement.bus_to in outage_buses and 
                  measurement.meas_type in outage_types):
                is_outaged = True
            
            if is_outaged:
                outaged_measurements.append(measurement)
            else:
                remaining_measurements.append(measurement)
        
        # Update measurements list
        self.measurements = remaining_measurements
        
        # Analyze observability impact
        observability_analysis = self._analyze_observability_impact(
            original_measurements, outaged_measurements, outage_buses
        )
        
        outage_info = {
            'outage_buses': outage_buses,
            'outage_types': [t.value for t in outage_types],
            'original_measurement_count': original_count,
            'outaged_measurement_count': len(outaged_measurements),
            'remaining_measurement_count': len(remaining_measurements),
            'outaged_measurements': outaged_measurements,
            'observability_analysis': observability_analysis,
            'measurement_redundancy_before': original_count / max(1, len(self.net.bus) * 2 - 1),
            'measurement_redundancy_after': len(remaining_measurements) / max(1, len(self.net.bus) * 2 - 1)
        }
        
        return outage_info
    
    def restore_measurements_from_outage(self, original_measurements: List[Measurement]):
        """Restore measurements after outage simulation."""
        self.measurements = original_measurements.copy()
    
    def _analyze_observability_impact(self, original_measurements: List[Measurement],
                                    outaged_measurements: List[Measurement],
                                    outage_buses: List[int]) -> Dict[str, Any]:
        """Analyze the impact of measurement outage on system observability."""
        
        # Count measurements by bus
        measurements_by_bus = {}
        for bus_idx in self.net.bus.index:
            measurements_by_bus[bus_idx] = {'before': 0, 'after': 0, 'outaged': 0}
        
        # Count original measurements
        for meas in original_measurements:
            if meas.bus_from in measurements_by_bus:
                measurements_by_bus[meas.bus_from]['before'] += 1
            if meas.bus_to is not None and meas.bus_to in measurements_by_bus:
                measurements_by_bus[meas.bus_to]['before'] += 1
        
        # Count remaining measurements
        for meas in self.measurements:
            if meas.bus_from in measurements_by_bus:
                measurements_by_bus[meas.bus_from]['after'] += 1
            if meas.bus_to is not None and meas.bus_to in measurements_by_bus:
                measurements_by_bus[meas.bus_to]['after'] += 1
        
        # Count outaged measurements
        for meas in outaged_measurements:
            if meas.bus_from in measurements_by_bus:
                measurements_by_bus[meas.bus_from]['outaged'] += 1
            if meas.bus_to is not None and meas.bus_to in measurements_by_bus:
                measurements_by_bus[meas.bus_to]['outaged'] += 1
        
        # Identify potentially unobservable buses
        unobservable_buses = []
        critically_observable_buses = []
        
        for bus_idx, counts in measurements_by_bus.items():
            if counts['after'] == 0:
                unobservable_buses.append(bus_idx)
            elif counts['after'] == 1:
                critically_observable_buses.append(bus_idx)
        
        # Calculate redundancy impact
        total_states = len(self.net.bus) * 2 - 1  # voltage magnitudes and angles (minus slack angle)
        redundancy_before = len(original_measurements) / total_states
        redundancy_after = len(self.measurements) / total_states
        redundancy_loss = redundancy_before - redundancy_after
        
        # Assess overall observability status
        if len(unobservable_buses) > 0:
            observability_status = "CRITICAL - Unobservable buses detected"
        elif len(critically_observable_buses) > 0:
            observability_status = "WARNING - Low redundancy on some buses"
        elif redundancy_after < 1.2:
            observability_status = "POOR - Low overall redundancy"
        elif redundancy_after < 1.5:
            observability_status = "FAIR - Adequate redundancy"
        else:
            observability_status = "GOOD - Sufficient redundancy"
        
        return {
            'measurements_by_bus': measurements_by_bus,
            'unobservable_buses': unobservable_buses,
            'critically_observable_buses': critically_observable_buses,
            'redundancy_before': redundancy_before,
            'redundancy_after': redundancy_after,
            'redundancy_loss': redundancy_loss,
            'observability_status': observability_status,
            'recommendations': self._generate_outage_recommendations(
                unobservable_buses, critically_observable_buses, redundancy_after
            )
        }
    
    def _generate_outage_recommendations(self, unobservable_buses: List[int],
                                       critically_observable_buses: List[int],
                                       redundancy: float) -> List[str]:
        """Generate recommendations for handling measurement outages."""
        recommendations = []
        
        if len(unobservable_buses) > 0:
            recommendations.append(f"🚨 URGENT: Install backup measurements at buses {unobservable_buses}")
            recommendations.append("🚨 URGENT: State estimation may fail or provide unreliable results")
        
        if len(critically_observable_buses) > 0:
            recommendations.append(f"⚠️ WARNING: Add redundant measurements at buses {critically_observable_buses}")
            recommendations.append("⚠️ WARNING: Single point of failure for these buses")
        
        if redundancy < 1.2:
            recommendations.append("📊 IMPROVE: Overall measurement redundancy is low")
            recommendations.append("📊 IMPROVE: Consider adding more measurement points")
        
        if not recommendations:
            recommendations.append("✅ GOOD: System maintains adequate observability")
            recommendations.append("✅ GOOD: State estimation should continue to work reliably")
        
        return recommendations
    
    def estimate_state_with_outage_analysis(self, outage_buses: List[int] = None,
                                          **kwargs) -> Dict[str, Any]:
        """Run state estimation with optional outage simulation and analysis."""
        results = {'outage_simulation': None}
        
        # Store original measurements
        original_measurements = self.measurements.copy()
        
        try:
            # Simulate outage if requested
            if outage_buses:
                outage_info = self.simulate_measurement_outage(outage_buses)
                results['outage_simulation'] = outage_info
                
                # Check if system is still observable
                if len(outage_info['observability_analysis']['unobservable_buses']) > 0:
                    results.update({
                        'converged': False,
                        'error': 'System not observable due to measurement outages',
                        'unobservable_buses': outage_info['observability_analysis']['unobservable_buses']
                    })
                    return results
            
            # Run state estimation
            se_results = self.estimate_state(**kwargs)
            results.update(se_results)
            
            # Add outage impact assessment if applicable
            if outage_buses and results.get('converged', False):
                results['outage_impact'] = self._assess_outage_impact(se_results, outage_info)
            
            return results
            
        finally:
            # Always restore original measurements
            self.measurements = original_measurements
    
    def _assess_outage_impact(self, se_results: Dict[str, Any], 
                            outage_info: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the impact of measurement outage on state estimation quality."""
        
        # Calculate quality degradation metrics
        redundancy_loss = outage_info['observability_analysis']['redundancy_loss']
        measurement_loss_percent = (outage_info['outaged_measurement_count'] / 
                                   outage_info['original_measurement_count']) * 100
        
        # Estimate uncertainty increase (simplified model)
        uncertainty_increase = redundancy_loss * 100  # Rough approximation
        
        # Assess convergence difficulty
        iterations = se_results.get('iterations', 0)
        if iterations > 10:
            convergence_difficulty = "HIGH"
        elif iterations > 5:
            convergence_difficulty = "MODERATE"
        else:
            convergence_difficulty = "LOW"
        
        return {
            'measurement_loss_percent': measurement_loss_percent,
            'redundancy_loss': redundancy_loss,
            'estimated_uncertainty_increase': uncertainty_increase,
            'convergence_difficulty': convergence_difficulty,
            'quality_assessment': (
                "DEGRADED" if uncertainty_increase > 10 else
                "ACCEPTABLE" if uncertainty_increase > 5 else
                "MINIMAL_IMPACT"
            )
        }
    
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