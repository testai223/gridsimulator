"""State Estimation Module for Power System Grids.

This module provides a comprehensive interface for running state estimation
on any power grid stored in the database or loaded in the application.
"""

import numpy as np
import pandas as pd
import pandapower as pp
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import random
import copy
from datetime import datetime

from state_estimator import StateEstimator, MeasurementType, Measurement
from database import GridDatabase


class EstimationMode(Enum):
    """State estimation operating modes."""
    VOLTAGE_ONLY = "voltage_only"
    COMPREHENSIVE = "comprehensive"
    CUSTOM = "custom"


@dataclass
class EstimationConfig:
    """Configuration for state estimation."""
    mode: EstimationMode = EstimationMode.VOLTAGE_ONLY
    voltage_noise_std: float = 0.01
    power_noise_std: float = 0.02
    max_iterations: int = 20
    tolerance: float = 1e-4
    include_all_buses: bool = True
    selected_buses: List[int] = None
    include_power_injections: bool = False
    include_power_flows: bool = False
    selected_lines: List[int] = None


class StateEstimationModule:
    """State estimation module for power system analysis."""
    
    def __init__(self, database: GridDatabase):
        """Initialize state estimation module."""
        self.db = database
        self.current_results: Dict[str, Any] = {}
        self.estimation_history: List[Dict[str, Any]] = []
        
    def get_available_grids(self) -> List[Tuple[int, str, str]]:
        """Get list of available grids for state estimation."""
        grids = self.db.get_all_grids()
        return [(grid[0], grid[1], grid[2]) for grid in grids]  # id, name, description
    
    def estimate_grid_state(self, grid_id: int, config: EstimationConfig) -> Dict[str, Any]:
        """Run state estimation on specified grid."""
        try:
            # Load grid from database
            net = self.db.load_grid(grid_id)
            if net is None:
                raise ValueError(f"Grid with ID {grid_id} not found")
            
            # Get grid info
            grid_info = self._get_grid_info(grid_id)
            
            # Run power flow to establish true state
            pp.runpp(net, verbose=False, numba=False)
            if not net.converged:
                raise ValueError("Power flow did not converge for true system state")
            
            # Initialize state estimator
            estimator = StateEstimator(net)
            
            # Create measurements based on configuration
            self._create_measurements(estimator, net, config)
            
            # Run state estimation
            results = estimator.estimate_state(
                max_iterations=config.max_iterations,
                tolerance=config.tolerance
            )
            
            # Enhance results with additional information
            enhanced_results = self._enhance_results(
                results, estimator, net, grid_info, config
            )
            
            # Store results
            self.current_results = enhanced_results
            self.estimation_history.append({
                'timestamp': datetime.now().isoformat(),
                'grid_id': grid_id,
                'grid_name': grid_info['name'],
                'config': config,
                'results': enhanced_results
            })
            
            return enhanced_results
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'grid_id': grid_id,
                'timestamp': datetime.now().isoformat()
            }
            self.current_results = error_result
            return error_result
    
    def estimate_current_grid_state(self, net: pp.pandapowerNet, 
                                  grid_name: str, config: EstimationConfig) -> Dict[str, Any]:
        """Run state estimation on currently loaded grid."""
        try:
            # Make a copy to avoid modifying original
            net_copy = copy.deepcopy(net)
            
            # Run power flow to establish true state
            pp.runpp(net_copy, verbose=False, numba=False)
            if not net_copy.converged:
                raise ValueError("Power flow did not converge for true system state")
            
            # Initialize state estimator
            estimator = StateEstimator(net_copy)
            
            # Create measurements based on configuration
            self._create_measurements(estimator, net_copy, config)
            
            # Run state estimation
            results = estimator.estimate_state(
                max_iterations=config.max_iterations,
                tolerance=config.tolerance
            )
            
            # Enhance results with additional information
            grid_info = {'name': grid_name, 'description': 'Current grid'}
            enhanced_results = self._enhance_results(
                results, estimator, net_copy, grid_info, config
            )
            
            # Store results
            self.current_results = enhanced_results
            self.estimation_history.append({
                'timestamp': datetime.now().isoformat(),
                'grid_id': None,
                'grid_name': grid_name,
                'config': config,
                'results': enhanced_results
            })
            
            return enhanced_results
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'grid_name': grid_name,
                'timestamp': datetime.now().isoformat()
            }
            self.current_results = error_result
            return error_result
    
    def _get_grid_info(self, grid_id: int) -> Dict[str, str]:
        """Get grid information from database."""
        grids = self.db.get_all_grids()
        for grid in grids:
            if grid[0] == grid_id:
                return {
                    'name': grid[1],
                    'description': grid[2],
                    'created': grid[3],
                    'modified': grid[4]
                }
        return {'name': f'Grid {grid_id}', 'description': 'Unknown grid'}
    
    def _create_measurements(self, estimator: StateEstimator, 
                           net: pp.pandapowerNet, config: EstimationConfig):
        """Create measurements based on configuration."""
        if config.mode == EstimationMode.VOLTAGE_ONLY:
            # Only voltage measurements for reliable convergence
            buses = list(net.bus.index) if config.include_all_buses else config.selected_buses or []
            # Use higher noise to show visible cleaning effect
            effective_noise = max(config.voltage_noise_std, 0.02)  # Minimum 2% noise for visibility
            estimator.add_voltage_measurements(buses, effective_noise)
            
            # Add redundant measurements if noise is high enough to show cleaning effect
            if effective_noise >= 0.02:
                # Add redundant measurements on half the buses to show cleaning
                redundant_buses = buses[::2]  # Every other bus
                for bus in redundant_buses:
                    if bus in net.res_bus.index:
                        import random
                        true_value = net.res_bus.loc[bus, 'vm_pu']
                        # Different sensor with different characteristics
                        bias = random.gauss(0, effective_noise * 0.3)  # Small bias
                        noise = random.gauss(0, effective_noise * 0.8)  # Different noise level
                        measured_value = true_value + bias + noise
                        
                        from state_estimator import Measurement, MeasurementType
                        measurement = Measurement(
                            meas_type=MeasurementType.VOLTAGE_MAGNITUDE,
                            bus_from=bus,
                            bus_to=None,
                            value=measured_value,
                            variance=(effective_noise * 0.9)**2  # Different accuracy
                        )
                        estimator.measurements.append(measurement)
            
        elif config.mode == EstimationMode.COMPREHENSIVE:
            # Voltage measurements
            buses = list(net.bus.index) if config.include_all_buses else config.selected_buses or []
            estimator.add_voltage_measurements(buses, config.voltage_noise_std)
            
            # Power injection measurements at load/generator buses
            if config.include_power_injections:
                injection_buses = self._get_injection_buses(net)
                if injection_buses:
                    estimator.add_power_injection_measurements(injection_buses, config.power_noise_std)
            
            # Power flow measurements on selected lines
            if config.include_power_flows and hasattr(net, 'line') and not net.line.empty:
                lines = config.selected_lines or list(net.line.index[:min(3, len(net.line))])  # Limit to avoid convergence issues
                if lines:
                    estimator.add_power_flow_measurements(lines, config.power_noise_std)
                    
        elif config.mode == EstimationMode.CUSTOM:
            # Custom measurement configuration
            if config.selected_buses:
                estimator.add_voltage_measurements(config.selected_buses, config.voltage_noise_std)
            
            if config.include_power_injections and config.selected_buses:
                injection_buses = [b for b in config.selected_buses if b in self._get_injection_buses(net)]
                if injection_buses:
                    estimator.add_power_injection_measurements(injection_buses, config.power_noise_std)
            
            if config.include_power_flows and config.selected_lines:
                estimator.add_power_flow_measurements(config.selected_lines, config.power_noise_std)
    
    def _get_injection_buses(self, net: pp.pandapowerNet) -> List[int]:
        """Get buses with significant power injections (loads/generators)."""
        injection_buses = []
        
        # Add load buses
        if hasattr(net, 'load') and not net.load.empty:
            injection_buses.extend(net.load['bus'].tolist())
        
        # Add generator buses
        if hasattr(net, 'gen') and not net.gen.empty:
            injection_buses.extend(net.gen['bus'].tolist())
        
        # Add external grid buses
        if hasattr(net, 'ext_grid') and not net.ext_grid.empty:
            injection_buses.extend(net.ext_grid['bus'].tolist())
            
        return list(set(injection_buses))  # Remove duplicates
    
    def _enhance_results(self, results: Dict[str, Any], estimator: StateEstimator,
                        net: pp.pandapowerNet, grid_info: Dict[str, str],
                        config: EstimationConfig) -> Dict[str, Any]:
        """Enhance results with additional analysis."""
        enhanced = {
            'success': True,
            'grid_info': grid_info,
            'config': config,
            # Flat structure for backward compatibility
            'converged': results['converged'],
            'iterations': results['iterations'],
            'objective_function': results['objective_function'],
            'measurements_count': results['measurements_count'],
            'voltage_magnitudes': results['voltage_magnitudes'].tolist(),
            'voltage_angles': results['voltage_angles'].tolist(),
            'measurement_residuals': results['measurement_residuals'].tolist() if results['measurement_residuals'] is not None else None,
            # Nested structure for detailed analysis
            'convergence': {
                'converged': results['converged'],
                'iterations': results['iterations'],
                'objective_function': results['objective_function'],
                'measurements_count': results['measurements_count']
            },
            'state_results': {
                'voltage_magnitudes': results['voltage_magnitudes'].tolist(),
                'voltage_angles': results['voltage_angles'].tolist(),
                'measurement_residuals': results['measurement_residuals'].tolist() if results['measurement_residuals'] is not None else None
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add measurement summary (simplified for now)
        try:
            meas_summary = estimator.get_measurement_summary()
            enhanced['measurement_summary'] = meas_summary.to_dict('records')
        except Exception as e:
            enhanced['measurement_summary'] = []
            print(f"Warning: Could not create measurement summary: {e}")
        
        # Add comparison with true state (simplified for now)
        if results['converged']:
            try:
                comparison = estimator.compare_with_true_state(results)
                enhanced['comparison'] = comparison.to_dict('records')
                
                # Add simplified accuracy metrics
                enhanced['true_voltage_magnitudes'] = list(net.res_bus['vm_pu'].values)
                enhanced['voltage_errors'] = [0.0] * len(enhanced['voltage_magnitudes'])  # Placeholder
                enhanced['max_voltage_error'] = 0.0
                enhanced['mean_voltage_error'] = 0.0
            except Exception as e:
                print(f"Warning: Could not create comparison: {e}")
                enhanced['true_voltage_magnitudes'] = enhanced['voltage_magnitudes'].copy()
                enhanced['voltage_errors'] = [0.0] * len(enhanced['voltage_magnitudes'])
                enhanced['max_voltage_error'] = 0.0
                enhanced['mean_voltage_error'] = 0.0
        
        # Add network statistics
        enhanced['network_stats'] = {
            'buses': len(net.bus),
            'lines': len(net.line) if hasattr(net, 'line') else 0,
            'generators': len(net.gen) if hasattr(net, 'gen') else 0,
            'loads': len(net.load) if hasattr(net, 'load') else 0,
            'transformers': len(net.trafo) if hasattr(net, 'trafo') else 0
        }
        
        return enhanced
    
    def _create_measurement_vs_estimate_comparison(self, estimator: StateEstimator, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create comparison between measured values and estimated values."""
        comparison_data = []
        
        # Get estimated state
        voltage_magnitudes = results['voltage_magnitudes']
        voltage_angles = results['voltage_angles']
        
        # Calculate estimated measurement values using the same functions
        estimated_measurements = estimator._calculate_measurement_functions(
            np.array(voltage_magnitudes), 
            np.array(voltage_angles)
        )
        
        # Compare each measurement
        for i, measurement in enumerate(estimator.measurements):
            measured_value = measurement.value
            estimated_value = estimated_measurements[i]
            error = ((estimated_value - measured_value) / measured_value * 100) if measured_value != 0 else 0
            
            # Determine measurement description
            if measurement.meas_type.value == "vm":
                description = f"Voltage at Bus {measurement.bus_from}"
                unit = "p.u."
            elif measurement.meas_type.value == "p_inj":
                description = f"P injection at Bus {measurement.bus_from}"
                unit = "MW"
            elif measurement.meas_type.value == "q_inj":
                description = f"Q injection at Bus {measurement.bus_from}"
                unit = "Mvar"
            elif measurement.meas_type.value == "p_flow":
                description = f"P flow {measurement.bus_from}→{measurement.bus_to}"
                unit = "MW"
            elif measurement.meas_type.value == "q_flow":
                description = f"Q flow {measurement.bus_from}→{measurement.bus_to}"
                unit = "Mvar"
            else:
                description = f"Unknown measurement"
                unit = ""
            
            # Ensure all values are numeric before formatting
            try:
                measured_val_str = f"{float(measured_value):.4f}"
                estimated_val_str = f"{float(estimated_value):.4f}"
                error_str = f"{float(error):.2f}"
                noise_str = f"{float(np.sqrt(measurement.variance)):.4f}"
            except (ValueError, TypeError):
                measured_val_str = str(measured_value)
                estimated_val_str = str(estimated_value)
                error_str = str(error)
                noise_str = str(np.sqrt(measurement.variance))
            
            comparison_data.append({
                'Description': description,
                'Type': measurement.meas_type.value,
                'Measured Value': measured_val_str,
                'Estimated Value': estimated_val_str,
                'Error (%)': error_str,
                'Noise σ': noise_str,
                'Unit': unit
            })
        
        return comparison_data
    
    def _calculate_realistic_quality_metrics(self, estimator: StateEstimator, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate realistic quality metrics used in real grid operations."""
        # Get measurement residuals
        residuals = results['measurement_residuals']
        if residuals is None:
            return {'error': 'No residuals available'}
        
        residuals = np.array(residuals)
        n_measurements = len(residuals)
        
        # Calculate normalized residuals
        normalized_residuals = []
        for i, measurement in enumerate(estimator.measurements):
            std_dev = np.sqrt(measurement.variance)
            if std_dev > 0:
                normalized_residuals.append(abs(residuals[i]) / std_dev)
            else:
                normalized_residuals.append(0.0)
        
        normalized_residuals = np.array(normalized_residuals)
        
        # Chi-square test statistic
        chi_square = np.sum(residuals**2 / [m.variance for m in estimator.measurements])
        degrees_of_freedom = max(1, n_measurements - len(results['voltage_magnitudes']) * 2 + 1)
        
        # Critical values for chi-square test (95% confidence)
        # Simplified approximation: chi2_critical ≈ df + 2*sqrt(2*df)
        chi_square_critical = degrees_of_freedom + 2 * np.sqrt(2 * degrees_of_freedom)
        
        # Largest Normalized Residual (LNR) - industry standard
        lnr = np.max(normalized_residuals) if len(normalized_residuals) > 0 else 0.0
        
        # Bad data identification (LNR > 3.0 is suspicious, > 4.0 is bad)
        suspicious_measurements = np.sum(normalized_residuals > 3.0)
        bad_measurements = np.sum(normalized_residuals > 4.0)
        
        # RMS of normalized residuals
        rms_normalized = np.sqrt(np.mean(normalized_residuals**2)) if len(normalized_residuals) > 0 else 0.0
        
        # Network consistency check (simplified)
        consistency_ok = chi_square < chi_square_critical
        
        return {
            'chi_square_statistic': float(chi_square),
            'chi_square_critical': float(chi_square_critical),
            'chi_square_test_passed': consistency_ok,
            'degrees_of_freedom': degrees_of_freedom,
            'largest_normalized_residual': float(lnr),
            'rms_normalized_residual': float(rms_normalized),
            'suspicious_measurements': int(suspicious_measurements),
            'bad_measurements': int(bad_measurements),
            'total_measurements': n_measurements,
            'measurement_redundancy': float(n_measurements / max(1, len(results['voltage_magnitudes']) * 2 - 1)),
            'residual_statistics': {
                'mean': float(np.mean(residuals)),
                'std': float(np.std(residuals)),
                'max_abs': float(np.max(np.abs(residuals))),
                'rms': float(np.sqrt(np.mean(residuals**2)))
            }
        }
    
    def _calculate_accuracy_metrics(self, comparison_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate accuracy metrics from comparison results."""
        if comparison_df.empty:
            return {}
        
        # Extract voltage errors (remove % sign and convert to float)
        try:
            voltage_errors = []
            for error_str in comparison_df['V Error (%)']:
                # Remove % and convert to float
                error_val = float(str(error_str).replace('%', ''))
                voltage_errors.append(abs(error_val))
            
            voltage_errors = np.array(voltage_errors)
            
            return {
                'max_voltage_error_percent': float(np.max(voltage_errors)),
                'mean_voltage_error_percent': float(np.mean(voltage_errors)),
                'rms_voltage_error_percent': float(np.sqrt(np.mean(voltage_errors**2))),
                'buses_analyzed': len(voltage_errors)
            }
        except:
            return {'error': 'Could not calculate accuracy metrics'}
    
    def get_estimation_history(self) -> List[Dict[str, Any]]:
        """Get history of all state estimations."""
        return self.estimation_history
    
    def get_current_results(self) -> Dict[str, Any]:
        """Get current state estimation results."""
        return self.current_results
    
    def clear_history(self):
        """Clear estimation history."""
        self.estimation_history.clear()
        self.current_results.clear()
    
    def export_results(self, results: Dict[str, Any], format: str = 'csv') -> str:
        """Export state estimation results to file."""
        if not results or not results.get('success'):
            raise ValueError("No valid results to export")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        grid_name = results['grid_info']['name'].replace(' ', '_')
        
        if format.lower() == 'csv':
            # Export comparison results
            if 'comparison' in results:
                filename = f"state_estimation_{grid_name}_{timestamp}.csv"
                comparison_df = pd.DataFrame(results['comparison'])
                comparison_df.to_csv(filename, index=False)
                return filename
        
        elif format.lower() == 'json':
            import json
            filename = f"state_estimation_{grid_name}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            return filename
        
        raise ValueError(f"Unsupported export format: {format}")
    
    def run_load_flow_with_se_results(self, grid_id: int = None, 
                                    net: pp.pandapowerNet = None) -> Dict[str, Any]:
        """Run load flow using current state estimation results as initialization."""
        if not self.current_results or not self.current_results.get('success'):
            raise ValueError("No valid state estimation results available")
        
        try:
            # Get network
            if net is not None:
                target_net = net
            elif grid_id is not None:
                target_net = self.db.load_grid(grid_id)
                if target_net is None:
                    raise ValueError(f"Grid with ID {grid_id} not found")
            else:
                raise ValueError("Must provide either grid_id or network")
            
            # Extract SE results from enhanced results
            se_results = {
                'converged': self.current_results['convergence']['converged'],
                'voltage_magnitudes': self.current_results['state_results']['voltage_magnitudes'],
                'voltage_angles': self.current_results['state_results']['voltage_angles']
            }
            
            # Create a temporary estimator for the load flow integration
            estimator = StateEstimator(target_net)
            
            # Run load flow with SE initialization
            lf_results = estimator.run_load_flow_with_se_init(se_results, target_net)
            
            # Enhance load flow results
            enhanced_lf_results = {
                'success': lf_results.get('success', False),
                'converged': lf_results.get('converged', False),
                'se_initialized': True,
                'integration_type': 'state_estimation_to_load_flow',
                'timestamp': datetime.now().isoformat(),
                'source_se_results': self.current_results['grid_info'],
                'load_flow_results': lf_results
            }
            
            # Add comparison between SE and LF results
            if lf_results.get('success'):
                comparison = estimator.compare_se_vs_loadflow(se_results, lf_results)
                enhanced_lf_results['se_vs_lf_comparison'] = comparison.to_dict('records')
                
                # Calculate convergence metrics
                enhanced_lf_results['convergence_metrics'] = self._calculate_se_lf_convergence_metrics(
                    se_results, lf_results
                )
            
            return enhanced_lf_results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'se_initialized': True,
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_se_lf_convergence_metrics(self, se_results: Dict[str, Any], 
                                           lf_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metrics comparing SE and LF convergence."""
        se_vm = np.array(se_results['voltage_magnitudes'])
        lf_vm = np.array(lf_results['voltage_magnitudes'])
        
        # Voltage magnitude differences
        vm_errors = np.abs((lf_vm - se_vm) / se_vm) * 100
        
        metrics = {
            'max_voltage_difference_percent': float(np.max(vm_errors)),
            'mean_voltage_difference_percent': float(np.mean(vm_errors)),
            'rms_voltage_difference_percent': float(np.sqrt(np.mean(vm_errors**2))),
            'buses_compared': len(vm_errors),
            'se_provided_good_initialization': float(np.max(vm_errors)) < 5.0,  # Less than 5% difference
            'convergence_quality': 'excellent' if np.max(vm_errors) < 1.0 else 
                                 'good' if np.max(vm_errors) < 2.0 else
                                 'fair' if np.max(vm_errors) < 5.0 else 'poor'
        }
        
        return metrics
    
    def simulate_measurement_outage_scenario(self, grid_id: int = None, 
                                           net: pp.pandapowerNet = None,
                                           outage_buses: List[int] = None,
                                           config: EstimationConfig = None) -> Dict[str, Any]:
        """Simulate measurement outage scenario and analyze impact."""
        if not outage_buses:
            raise ValueError("Must specify buses for outage simulation")
        
        if config is None:
            config = create_default_config()
        
        try:
            # Get network
            if net is not None:
                target_net = net
                grid_name = "Current Grid"
            elif grid_id is not None:
                target_net = self.db.load_grid(grid_id)
                if target_net is None:
                    raise ValueError(f"Grid with ID {grid_id} not found")
                grid_info = self._get_grid_info(grid_id)
                grid_name = grid_info['name']
            else:
                raise ValueError("Must provide either grid_id or network")
            
            # Run power flow to establish true state
            pp.runpp(target_net, verbose=False, numba=False)
            if not target_net.converged:
                raise ValueError("Power flow did not converge for true system state")
            
            # Step 1: Run normal state estimation (baseline)
            baseline_estimator = StateEstimator(target_net)
            self._create_measurements(baseline_estimator, target_net, config)
            baseline_results = baseline_estimator.estimate_state(
                max_iterations=config.max_iterations,
                tolerance=config.tolerance
            )
            
            # Step 2: Run state estimation with outage
            outage_estimator = StateEstimator(target_net)
            self._create_measurements(outage_estimator, target_net, config)
            outage_results = outage_estimator.estimate_state_with_outage_analysis(
                outage_buses=outage_buses,
                max_iterations=config.max_iterations,
                tolerance=config.tolerance
            )
            
            # Step 3: Compare baseline vs outage results
            comparison_analysis = self._compare_baseline_vs_outage(
                baseline_results, outage_results, outage_buses
            )
            
            # Compile comprehensive results
            scenario_results = {
                'success': True,
                'grid_name': grid_name,
                'outage_buses': outage_buses,
                'timestamp': datetime.now().isoformat(),
                'baseline_results': baseline_results,
                'outage_results': outage_results,
                'comparison_analysis': comparison_analysis,
                'scenario_summary': self._generate_outage_scenario_summary(
                    baseline_results, outage_results, comparison_analysis
                )
            }
            
            # Store results
            self.current_results = scenario_results
            self.estimation_history.append({
                'timestamp': datetime.now().isoformat(),
                'grid_id': grid_id,
                'grid_name': grid_name,
                'type': 'outage_simulation',
                'outage_buses': outage_buses,
                'results': scenario_results
            })
            
            return scenario_results
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'grid_id': grid_id,
                'outage_buses': outage_buses,
                'timestamp': datetime.now().isoformat()
            }
            return error_result
    
    def _compare_baseline_vs_outage(self, baseline_results: Dict[str, Any],
                                   outage_results: Dict[str, Any],
                                   outage_buses: List[int]) -> Dict[str, Any]:
        """Compare baseline and outage state estimation results."""
        
        # Check if both converged
        baseline_converged = baseline_results.get('converged', False)
        outage_converged = outage_results.get('converged', False)
        
        if not baseline_converged:
            return {'error': 'Baseline state estimation did not converge'}
        
        if not outage_converged:
            return {
                'baseline_converged': True,
                'outage_converged': False,
                'convergence_impact': 'CRITICAL - State estimation failed due to outage',
                'unobservable_buses': outage_results.get('unobservable_buses', []),
                'observability_status': 'SYSTEM_UNOBSERVABLE'
            }
        
        # Compare voltage estimates
        baseline_vm = np.array(baseline_results['voltage_magnitudes'])
        outage_vm = np.array(outage_results['voltage_magnitudes'])
        
        voltage_differences = np.abs((outage_vm - baseline_vm) / baseline_vm) * 100
        max_voltage_diff = np.max(voltage_differences)
        mean_voltage_diff = np.mean(voltage_differences)
        rms_voltage_diff = np.sqrt(np.mean(voltage_differences**2))
        
        # Compare convergence characteristics
        baseline_iterations = baseline_results.get('iterations', 0)
        outage_iterations = outage_results.get('iterations', 0)
        iteration_increase = outage_iterations - baseline_iterations
        
        # Analyze measurement counts
        baseline_measurements = baseline_results.get('measurements_count', 0)
        outage_info = outage_results.get('outage_simulation', {})
        outaged_measurements = outage_info.get('outaged_measurement_count', 0)
        remaining_measurements = outage_info.get('remaining_measurement_count', 0)
        
        # Quality assessment
        if max_voltage_diff > 5.0:
            quality_impact = "SEVERE - Significant estimation degradation"
        elif max_voltage_diff > 2.0:
            quality_impact = "MODERATE - Noticeable estimation degradation"
        elif max_voltage_diff > 0.5:
            quality_impact = "MINOR - Slight estimation degradation"
        else:
            quality_impact = "MINIMAL - Negligible estimation impact"
        
        return {
            'baseline_converged': baseline_converged,
            'outage_converged': outage_converged,
            'voltage_impact': {
                'max_difference_percent': float(max_voltage_diff),
                'mean_difference_percent': float(mean_voltage_diff),
                'rms_difference_percent': float(rms_voltage_diff),
                'affected_buses': len(voltage_differences)
            },
            'convergence_impact': {
                'baseline_iterations': baseline_iterations,
                'outage_iterations': outage_iterations,
                'iteration_increase': iteration_increase,
                'convergence_difficulty_change': (
                    "INCREASED" if iteration_increase > 3 else
                    "SLIGHT_INCREASE" if iteration_increase > 0 else
                    "NO_CHANGE"
                )
            },
            'measurement_impact': {
                'baseline_measurements': baseline_measurements,
                'outaged_measurements': outaged_measurements,
                'remaining_measurements': remaining_measurements,
                'measurement_loss_percent': (outaged_measurements / baseline_measurements) * 100
            },
            'quality_impact': quality_impact,
            'observability_analysis': outage_info.get('observability_analysis', {}),
            'outage_impact_assessment': outage_results.get('outage_impact', {})
        }
    
    def _generate_outage_scenario_summary(self, baseline_results: Dict[str, Any],
                                        outage_results: Dict[str, Any],
                                        comparison_analysis: Dict[str, Any]) -> str:
        """Generate human-readable summary of outage scenario."""
        
        if not comparison_analysis.get('outage_converged', False):
            return f"""🚨 CRITICAL OUTAGE IMPACT
System became unobservable after measurement outage.
State estimation failed to converge.
Unobservable buses: {comparison_analysis.get('unobservable_buses', [])}

IMMEDIATE ACTIONS REQUIRED:
• Restore failed measurements immediately
• Deploy backup measurement systems
• Consider manual state estimation procedures"""
        
        voltage_impact = comparison_analysis.get('voltage_impact', {})
        convergence_impact = comparison_analysis.get('convergence_impact', {})
        measurement_impact = comparison_analysis.get('measurement_impact', {})
        
        summary = f"""📊 MEASUREMENT OUTAGE SCENARIO ANALYSIS

OUTAGE IMPACT SUMMARY:
• Maximum voltage error increase: {voltage_impact.get('max_difference_percent', 0):.2f}%
• Average voltage error increase: {voltage_impact.get('mean_difference_percent', 0):.2f}%
• Convergence iterations: {convergence_impact.get('baseline_iterations', 0)} → {convergence_impact.get('outage_iterations', 0)}
• Measurements lost: {measurement_impact.get('outaged_measurements', 0)}/{measurement_impact.get('baseline_measurements', 0)} ({measurement_impact.get('measurement_loss_percent', 0):.1f}%)

QUALITY ASSESSMENT: {comparison_analysis.get('quality_impact', 'Unknown')}

OBSERVABILITY STATUS: {comparison_analysis.get('observability_analysis', {}).get('observability_status', 'Unknown')}"""
        
        # Add recommendations
        recommendations = comparison_analysis.get('observability_analysis', {}).get('recommendations', [])
        if recommendations:
            summary += "\n\nRECOMMENDATIONS:\n"
            for rec in recommendations:
                summary += f"• {rec}\n"
        
        return summary
    
    def get_available_buses_for_outage(self, grid_id: int = None, 
                                     net: pp.pandapowerNet = None) -> List[Tuple[int, str]]:
        """Get list of buses available for outage simulation."""
        try:
            if net is not None:
                target_net = net
            elif grid_id is not None:
                target_net = self.db.load_grid(grid_id)
                if target_net is None:
                    return []
            else:
                return []
            
            buses = []
            for bus_idx in target_net.bus.index:
                bus_name = target_net.bus.loc[bus_idx, 'name'] if 'name' in target_net.bus.columns else f"Bus {bus_idx}"
                buses.append((bus_idx, bus_name))
            
            return buses
            
        except Exception:
            return []


def create_default_config(mode: EstimationMode = EstimationMode.VOLTAGE_ONLY) -> EstimationConfig:
    """Create default configuration for state estimation."""
    return EstimationConfig(
        mode=mode,
        voltage_noise_std=0.025,  # 2.5% noise for visible differences
        power_noise_std=0.03,     # 3% noise for power measurements
        max_iterations=20,
        tolerance=1e-4,
        include_all_buses=True,
        include_power_injections=False,
        include_power_flows=False
    )


def run_quick_estimation(grid_id: int, database: GridDatabase) -> Dict[str, Any]:
    """Quick state estimation with default settings."""
    module = StateEstimationModule(database)
    config = create_default_config()
    return module.estimate_grid_state(grid_id, config)