"""Contingency analysis module for power system outage studies."""

from typing import List, Dict, Any, Tuple, Optional
import copy
import pandas as pd
import pandapower as pp


class ContingencyAnalysis:
    """Perform N-1 contingency analysis on power systems."""

    def __init__(self, base_net: pp.pandapowerNet):
        """Initialize with base case network."""
        self.base_net = copy.deepcopy(base_net)
        self.contingency_results = []
        self.violations = []

    def run_n1_analysis(self) -> List[Dict[str, Any]]:
        """
        Run N-1 contingency analysis for all critical elements.
        Returns list of contingency results.
        """
        self.contingency_results = []
        self.violations = []
        
        # Run base case first
        base_result = self._analyze_base_case()
        if base_result:
            self.contingency_results.append(base_result)
        
        # Analyze line outages
        line_results = self._analyze_line_outages()
        self.contingency_results.extend(line_results)
        
        # Analyze transformer outages
        trafo_results = self._analyze_transformer_outages()
        self.contingency_results.extend(trafo_results)
        
        # Analyze generator outages
        gen_results = self._analyze_generator_outages()
        self.contingency_results.extend(gen_results)
        
        return self.contingency_results

    def _analyze_base_case(self) -> Optional[Dict[str, Any]]:
        """Analyze base case (no outages)."""
        try:
            net = copy.deepcopy(self.base_net)
            pp.runpp(net)
            
            result = {
                'contingency_type': 'Base Case',
                'element_id': None,
                'element_name': 'No outages',
                'converged': True,
                'max_voltage_pu': float(net.res_bus['vm_pu'].max()),
                'min_voltage_pu': float(net.res_bus['vm_pu'].min()),
                'max_line_loading': float(net.res_line['loading_percent'].max()) if not net.res_line.empty else 0.0,
                'max_trafo_loading': float(net.res_trafo['loading_percent'].max()) if hasattr(net, 'res_trafo') and not net.res_trafo.empty else 0.0,
                'total_generation_mw': float(net.res_gen['p_mw'].sum()) if hasattr(net, 'res_gen') and not net.res_gen.empty else 0.0,
                'total_load_mw': float(net.load['p_mw'].sum()) if hasattr(net, 'load') and not net.load.empty else 0.0,
                'voltage_violations': self._count_voltage_violations(net),
                'overload_violations': self._count_overload_violations(net)
            }
            
            # Assess severity for base case
            result['severity'] = self._assess_severity(result)
            
            # Collect detailed violations if any exist for base case
            if result['voltage_violations'] > 0 or result['overload_violations'] > 0:
                self._collect_detailed_violations(net, 'Base Case', 'No outages')
            
            return result
        except Exception as e:
            return {
                'contingency_type': 'Base Case',
                'element_id': None,
                'element_name': 'No outages',
                'converged': False,
                'error': str(e),
                'severity': 'Critical'
            }

    def _analyze_line_outages(self) -> List[Dict[str, Any]]:
        """Analyze individual line outages."""
        results = []
        
        for line_id in self.base_net.line.index:
            try:
                net = copy.deepcopy(self.base_net)
                line_name = net.line.loc[line_id, 'name'] if 'name' in net.line.columns else f"Line {line_id}"
                
                # Remove line by setting in_service to False
                net.line.loc[line_id, 'in_service'] = False
                
                pp.runpp(net)
                
                result = {
                    'contingency_type': 'Line Outage',
                    'element_id': int(line_id),
                    'element_name': line_name,
                    'converged': True,
                    'max_voltage_pu': float(net.res_bus['vm_pu'].max()),
                    'min_voltage_pu': float(net.res_bus['vm_pu'].min()),
                    'max_line_loading': float(net.res_line['loading_percent'].max()) if not net.res_line.empty else 0.0,
                    'max_trafo_loading': float(net.res_trafo['loading_percent'].max()) if hasattr(net, 'res_trafo') and not net.res_trafo.empty else 0.0,
                    'total_generation_mw': float(net.res_gen['p_mw'].sum()) if hasattr(net, 'res_gen') and not net.res_gen.empty else 0.0,
                    'total_load_mw': float(net.load['p_mw'].sum()) if hasattr(net, 'load') and not net.load.empty else 0.0,
                    'voltage_violations': self._count_voltage_violations(net),
                    'overload_violations': self._count_overload_violations(net)
                }
                
                # Determine severity
                result['severity'] = self._assess_severity(result)
                results.append(result)
                
                # Collect detailed violations if any exist
                if result['voltage_violations'] > 0 or result['overload_violations'] > 0:
                    self._collect_detailed_violations(net, 'Line Outage', line_name)
                
            except Exception as e:
                results.append({
                    'contingency_type': 'Line Outage',
                    'element_id': int(line_id),
                    'element_name': line_name,
                    'converged': False,
                    'error': str(e),
                    'severity': 'Critical'
                })
        
        return results

    def _analyze_transformer_outages(self) -> List[Dict[str, Any]]:
        """Analyze individual transformer outages."""
        results = []
        
        if not hasattr(self.base_net, 'trafo') or self.base_net.trafo.empty:
            return results
        
        for trafo_id in self.base_net.trafo.index:
            try:
                net = copy.deepcopy(self.base_net)
                trafo_name = net.trafo.loc[trafo_id, 'name'] if 'name' in net.trafo.columns else f"Trafo {trafo_id}"
                
                # Remove transformer by setting in_service to False
                net.trafo.loc[trafo_id, 'in_service'] = False
                
                pp.runpp(net)
                
                result = {
                    'contingency_type': 'Transformer Outage',
                    'element_id': int(trafo_id),
                    'element_name': trafo_name,
                    'converged': True,
                    'max_voltage_pu': float(net.res_bus['vm_pu'].max()),
                    'min_voltage_pu': float(net.res_bus['vm_pu'].min()),
                    'max_line_loading': float(net.res_line['loading_percent'].max()) if not net.res_line.empty else 0.0,
                    'max_trafo_loading': float(net.res_trafo['loading_percent'].max()) if hasattr(net, 'res_trafo') and not net.res_trafo.empty else 0.0,
                    'total_generation_mw': float(net.res_gen['p_mw'].sum()) if hasattr(net, 'res_gen') and not net.res_gen.empty else 0.0,
                    'total_load_mw': float(net.load['p_mw'].sum()) if hasattr(net, 'load') and not net.load.empty else 0.0,
                    'voltage_violations': self._count_voltage_violations(net),
                    'overload_violations': self._count_overload_violations(net)
                }
                
                result['severity'] = self._assess_severity(result)
                results.append(result)
                
                # Collect detailed violations if any exist
                if result['voltage_violations'] > 0 or result['overload_violations'] > 0:
                    self._collect_detailed_violations(net, 'Transformer Outage', trafo_name)
                
            except Exception as e:
                results.append({
                    'contingency_type': 'Transformer Outage',
                    'element_id': int(trafo_id),
                    'element_name': trafo_name,
                    'converged': False,
                    'error': str(e),
                    'severity': 'Critical'
                })
        
        return results

    def _analyze_generator_outages(self) -> List[Dict[str, Any]]:
        """Analyze individual generator outages (excluding slack generators)."""
        results = []
        
        if not hasattr(self.base_net, 'gen') or self.base_net.gen.empty:
            return results
        
        for gen_id in self.base_net.gen.index:
            try:
                net = copy.deepcopy(self.base_net)
                gen_name = net.gen.loc[gen_id, 'name'] if 'name' in net.gen.columns else f"Gen {gen_id}"
                
                # Skip slack generators to avoid convergence issues
                if net.gen.loc[gen_id, 'slack']:
                    continue
                
                # Remove generator by setting in_service to False
                net.gen.loc[gen_id, 'in_service'] = False
                
                pp.runpp(net)
                
                result = {
                    'contingency_type': 'Generator Outage',
                    'element_id': int(gen_id),
                    'element_name': gen_name,
                    'converged': True,
                    'max_voltage_pu': float(net.res_bus['vm_pu'].max()),
                    'min_voltage_pu': float(net.res_bus['vm_pu'].min()),
                    'max_line_loading': float(net.res_line['loading_percent'].max()) if not net.res_line.empty else 0.0,
                    'max_trafo_loading': float(net.res_trafo['loading_percent'].max()) if hasattr(net, 'res_trafo') and not net.res_trafo.empty else 0.0,
                    'total_generation_mw': float(net.res_gen['p_mw'].sum()) if hasattr(net, 'res_gen') and not net.res_gen.empty else 0.0,
                    'total_load_mw': float(net.load['p_mw'].sum()) if hasattr(net, 'load') and not net.load.empty else 0.0,
                    'voltage_violations': self._count_voltage_violations(net),
                    'overload_violations': self._count_overload_violations(net)
                }
                
                result['severity'] = self._assess_severity(result)
                results.append(result)
                
                # Collect detailed violations if any exist
                if result['voltage_violations'] > 0 or result['overload_violations'] > 0:
                    self._collect_detailed_violations(net, 'Generator Outage', gen_name)
                
            except Exception as e:
                results.append({
                    'contingency_type': 'Generator Outage',
                    'element_id': int(gen_id),
                    'element_name': gen_name,
                    'converged': False,
                    'error': str(e),
                    'severity': 'Critical'
                })
        
        return results

    def _count_voltage_violations(self, net: pp.pandapowerNet) -> int:
        """Count voltage violations (outside 0.97-1.03 p.u. range)."""
        violations = 0
        for vm in net.res_bus['vm_pu']:
            if vm < 0.97 or vm > 1.03:
                violations += 1
        return violations

    def _collect_detailed_violations(self, net: pp.pandapowerNet, contingency_type: str, element_name: str) -> None:
        """Collect detailed violation information for violations table."""
        # Voltage violations
        for bus_id, row in net.res_bus.iterrows():
            vm_pu = row['vm_pu']
            if vm_pu < 0.97 or vm_pu > 1.03:
                bus_name = net.bus.loc[bus_id, 'name'] if 'name' in net.bus.columns else f"Bus {bus_id}"
                violation_type = "Low Voltage" if vm_pu < 0.97 else "High Voltage"
                self.violations.append({
                    'contingency_type': contingency_type,
                    'contingency_element': element_name,
                    'violation_type': violation_type,
                    'element_type': 'Bus',
                    'element_id': int(bus_id),
                    'element_name': bus_name,
                    'violation_value': f"{vm_pu:.3f} p.u.",
                    'limit_value': "0.97-1.03 p.u.",
                    'severity': 'Critical' if vm_pu < 0.95 or vm_pu > 1.05 else 'High'
                })
        
        # Line overload violations
        if not net.res_line.empty:
            for line_id, row in net.res_line.iterrows():
                if line_id in net.line.index and net.line.loc[line_id, 'in_service']:
                    loading = row['loading_percent']
                    if loading > 85:
                        line_name = net.line.loc[line_id, 'name'] if 'name' in net.line.columns else f"Line {line_id}"
                        self.violations.append({
                            'contingency_type': contingency_type,
                            'contingency_element': element_name,
                            'violation_type': 'Overload',
                            'element_type': 'Line',
                            'element_id': int(line_id),
                            'element_name': line_name,
                            'violation_value': f"{loading:.1f}%",
                            'limit_value': "85%",
                            'severity': 'Critical' if loading > 120 else 'High'
                        })
        
        # Transformer overload violations
        if hasattr(net, 'res_trafo') and not net.res_trafo.empty:
            for trafo_id, row in net.res_trafo.iterrows():
                if trafo_id in net.trafo.index and net.trafo.loc[trafo_id, 'in_service']:
                    loading = row['loading_percent']
                    if loading > 85:
                        trafo_name = net.trafo.loc[trafo_id, 'name'] if 'name' in net.trafo.columns else f"Trafo {trafo_id}"
                        self.violations.append({
                            'contingency_type': contingency_type,
                            'contingency_element': element_name,
                            'violation_type': 'Overload',
                            'element_type': 'Transformer',
                            'element_id': int(trafo_id),
                            'element_name': trafo_name,
                            'violation_value': f"{loading:.1f}%",
                            'limit_value': "85%",
                            'severity': 'Critical' if loading > 120 else 'High'
                        })

    def _count_overload_violations(self, net: pp.pandapowerNet) -> int:
        """Count overload violations (>85% loading)."""
        violations = 0
        
        # Check line loadings
        if not net.res_line.empty:
            violations += len(net.res_line[net.res_line['loading_percent'] > 85])
        
        # Check transformer loadings
        if hasattr(net, 'res_trafo') and not net.res_trafo.empty:
            violations += len(net.res_trafo[net.res_trafo['loading_percent'] > 85])
        
        return violations

    def _assess_severity(self, result: Dict[str, Any]) -> str:
        """Assess contingency severity based on violations and operating limits."""
        if not result['converged']:
            return 'Critical'
        
        if result['voltage_violations'] > 0 or result['overload_violations'] > 0:
            return 'High'
        
        if result['max_voltage_pu'] > 1.02 or result['min_voltage_pu'] < 0.98:
            return 'Medium'
        
        if result['max_line_loading'] > 75 or result['max_trafo_loading'] > 75:
            return 'Medium'
        
        return 'Low'

    def get_critical_contingencies(self) -> List[Dict[str, Any]]:
        """Return contingencies with high or critical severity."""
        return [c for c in self.contingency_results if c['severity'] in ['High', 'Critical']]

    def get_contingency_summary(self) -> Dict[str, Any]:
        """Return summary statistics of contingency analysis."""
        if not self.contingency_results:
            return {}
        
        total = len(self.contingency_results)
        converged = len([c for c in self.contingency_results if c['converged']])
        critical = len([c for c in self.contingency_results if c['severity'] == 'Critical'])
        high = len([c for c in self.contingency_results if c['severity'] == 'High'])
        medium = len([c for c in self.contingency_results if c['severity'] == 'Medium'])
        low = len([c for c in self.contingency_results if c['severity'] == 'Low'])
        
        return {
            'total_contingencies': total,
            'converged_cases': converged,
            'convergence_rate': f"{converged/total*100:.1f}%",
            'critical_contingencies': critical,
            'high_severity': high,
            'medium_severity': medium,
            'low_severity': low,
            'security_status': 'Secure' if critical == 0 and high == 0 else 'Insecure'
        }