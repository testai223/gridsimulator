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
            estimator.add_voltage_measurements(buses, config.voltage_noise_std)
            
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
        
        # Add measurement summary
        meas_summary = estimator.get_measurement_summary()
        enhanced['measurement_summary'] = meas_summary.to_dict('records')
        
        # Add measurement vs estimate comparison
        if results['converged']:
            meas_vs_est = self._create_measurement_vs_estimate_comparison(estimator, results)
            enhanced['measurement_vs_estimate'] = meas_vs_est
        
        # Add comparison with true state
        if results['converged']:
            comparison = estimator.compare_with_true_state(results)
            enhanced['comparison'] = comparison.to_dict('records')
            
            # Calculate accuracy metrics
            enhanced['accuracy_metrics'] = self._calculate_accuracy_metrics(comparison)
        
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
            
            comparison_data.append({
                'Description': description,
                'Type': measurement.meas_type.value,
                'Measured Value': f"{measured_value:.4f}",
                'Estimated Value': f"{estimated_value:.4f}",
                'Error (%)': f"{error:.2f}",
                'Noise σ': f"{np.sqrt(measurement.variance):.4f}",
                'Unit': unit
            })
        
        return comparison_data
    
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


def create_default_config(mode: EstimationMode = EstimationMode.VOLTAGE_ONLY) -> EstimationConfig:
    """Create default configuration for state estimation."""
    return EstimationConfig(
        mode=mode,
        voltage_noise_std=0.01,
        power_noise_std=0.02,
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