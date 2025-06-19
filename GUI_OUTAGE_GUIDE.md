# 🚨 Outage Simulation - Where to Find Results

## Step-by-Step Guide to See Outage Results

### 1. Navigate to State Estimation Tab
```
Main GUI Window → State Estimation Tab (top tabs)
```

### 2. Select a Grid
```
Grid Selection dropdown → Choose "IEEE 9-Bus Test System"
```

### 3. Click Simulate Outage Button
```
Button row → "Simulate Outage" (blue button next to "SE → Load Flow")
```

### 4. Outage Selection Dialog Opens
```
Dialog shows:
- Title: "🚨 Measurement Outage Simulation"
- Bus selection checkboxes (Bus 0-8)
- Quick selection buttons
- Run Simulation button
```

### 5. Select Bus(es) for Outage
```
✅ Check one or more buses (e.g., Bus 0)
Click "Run Simulation"
```

### 6. **RESULTS APPEAR HERE** ⬇️
```
Main Results Area (large text box at bottom of State Estimation tab)

You should see:
================================================
Measurement Outage Simulation Results
==================================================
Grid: IEEE 9-Bus Test System
Outaged Buses: 0
Impact Status: ❌ FAILED - System became unobservable
Quick Assessment: Unobservable buses: [0]
Time: 2025-06-09T22:59:42

SCENARIO ANALYSIS:
------------------------------
🚨 CRITICAL OUTAGE IMPACT
System became unobservable after measurement outage.
State estimation failed to converge.
Unobservable buses: [0]

IMMEDIATE ACTIONS REQUIRED:
• Restore failed measurements immediately
• Deploy backup measurement systems
• Consider manual state estimation procedures
================================================
```

### 7. View Detailed Results
```
Click "View Results" button → Opens detailed analysis window
```

## 🔍 Troubleshooting - If You Don't See Results

### Check These Locations:

1. **Status Label** (below buttons):
   - Should show: "Outage simulation completed - Impact: CRITICAL"
   - If shows error: Check error message

2. **Main Results Text Area**:
   - Large scrollable text box at bottom
   - Should be cleared and show new outage results
   - Scroll up/down if needed

3. **Dialog Completion**:
   - Make sure outage dialog actually closed
   - Check that you clicked "Run Simulation" not "Cancel"

### Common Issues:

❌ **No Grid Selected**: Select a grid first  
❌ **No Buses Selected**: Check at least one bus in dialog  
❌ **Wrong Tab**: Make sure you're in "State Estimation" tab  
❌ **Results Scrolled**: Scroll in results area to see new content  

## 🎯 What Results Mean

### ❌ FAILED - System became unobservable
- **This is NORMAL and EDUCATIONAL**
- Shows what happens when critical sensors fail
- Demonstrates need for backup measurements
- Click "View Results" for recovery recommendations

### ✅ CONVERGED - (with error percentage)
- State estimation still worked despite outage
- Shows voltage estimation degradation
- Indicates system has sufficient redundancy

## 📊 Example Expected Results

Most single-bus outages on IEEE 9-Bus system will show:
```
Impact Status: ❌ FAILED - System became unobservable
Quick Assessment: Unobservable buses: [X]
```

This is **realistic behavior** - real power grids lose observability when critical measurements fail!

## 🎓 Educational Value

The outage simulation teaches:
- Why measurement redundancy is critical
- How sensor failures affect grid operations  
- Emergency response procedures
- Risk assessment for critical infrastructure

## 💡 Next Steps

1. Try different bus combinations
2. Use "View Results" for detailed analysis
3. Read the operational recommendations
4. Understand why backup systems are essential