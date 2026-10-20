import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Downhole Dysfunction Engine", layout="wide")
st.title("⚡ Downhole Telemetry Dysfunction Detection Engine")
st.markdown("*Real-time sliding-window anomaly detection for torsional resonance & stick-slip cycles.*")

# 1. Generate Telemetry Stream
@st.cache_data
def load_data():
    np.random.seed(42)
    n_steps = 1000
    time = np.arange(n_steps)
    torque = 50 + np.random.normal(0, 2, n_steps)
    vibration = 1.0 + np.random.normal(0, 0.1, n_steps)
    # Inject stick-slip event (steps 600-750)
    torque[600:750] += np.sin(np.linspace(0, 40, 150)) * 25 + np.random.normal(0, 5, 150)
    vibration[600:750] += np.random.exponential(2.5, 150)
    return pd.DataFrame({'time': time, 'torque': torque, 'vibration': vibration})

df = load_data()

# 2. Sidebar Controls
st.sidebar.header("Sliding Window Parameters")
window_size = st.sidebar.slider("Window Size (samples)", 10, 100, 30)
var_threshold = st.sidebar.slider("Variance Threshold", 1.0, 10.0, 4.0)

# 3. Processing Loop
results = []
for i in range(window_size, len(df)):
    window = df['vibration'].iloc[i-window_size:i]
    roll_var = np.var(window)
    papr = np.max(np.abs(window)) / (np.mean(np.abs(window)) + 1e-9)
    
    if roll_var > var_threshold or papr > 2.8:
        results.append({
            'time_step': df['time'].iloc[i],
            'variance': round(roll_var, 2),
            'PAPR': round(papr, 2),
            'status': 'WARNING: Stick-Slip / Resonance'
        })

anomalies_df = pd.DataFrame(results)

# 4. Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Streaming Telemetry (Vibration & Torque)")
    st.line_chart(df.set_index('time')[['vibration', 'torque']])

with col2:
    st.subheader("Detected Anomaly Windows")
    st.metric("Total Flagged Windows", len(anomalies_df))
    st.dataframe(anomalies_df.head(10), use_container_width=True)
