import streamlit as st
import logging
from app.main.python.ui import dashboard_widgets
from app.main.python import main, config
import time
from streamlit_autorefresh import st_autorefresh


# Initializations
main.initialize()
st.set_option('deprecation.showPyplotGlobalUse', False)


st.write("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nanum Gothic');
html, body, [class*="css"]{
   font-family: 'Nanum Gothic';
}
#tanzu-realtime-anomaly-detection-demo{
   color: #6a6161;
}
.blinking {
  animation: blinker 1s linear infinite;
  background: url('https://github.com/agapebondservant/tanzu-realtime-anomaly-detetction/blob/main/app/assets/clock.png?raw=true') no-repeat right;
}

@keyframes blinker {
  50% {
    opacity: 0;
  }
}
</style>
""", unsafe_allow_html=True)

st.header('Tanzu/Vmware Realtime Anomaly Detection Demo')

st.text('Near-realtime showcase of sentiment-based anomaly detection using Vmware RabbitMQ')

placeholder_tab1, placeholder_tab2, placeholder_tab3 = st.empty(), st.empty(), st.empty()

tab1, tab2, tab3 = st.tabs(["Home", "Feedback", "Anomalies"])

# Charts
base_key = time.time()
with tab1:
    logging.info("Refreshing dashboard...")

    timeframe = st.selectbox('Select time period', ('day', 'hour', 'week'))

    st.markdown("<div class='blinking'>&nbsp;</div>", unsafe_allow_html=True)

    dashboard_widgets.render_trends_dashboard(timeframe)

# Posts
with tab2:

    if 'sentiment_post' not in st.session_state:
        st.session_state['sentiment_post'] = ''
    if 'sentiment' not in st.session_state:
        st.session_state['sentiment'] = 'none'

    sentiment_mappings = {'positive': 'color:green', 'negative': 'color:red', 'neutral': 'color:gray', 'none': 'visibility:hidden'}

    st.write("Enter your thoughts:")

    st.text_input('Feedback', '''''', key='sentiment_post', on_change=dashboard_widgets.show_sentiment)

    st.markdown(
        f"Sentiment:<br/><span style=font-size:1.6em;{sentiment_mappings[st.session_state['sentiment']]}>{st.session_state['sentiment']}</span>",
        unsafe_allow_html=True)

    dashboard_widgets.render_sentiment_analysis_dashboard()

# Anomalies
with tab3:
    timeframe2 = st.selectbox('Select a time period', ('day', 'hour', 'week'))

    st.markdown("<div class='blinking'>&nbsp;</div>", unsafe_allow_html=True)

    dashboard_widgets.render_anomaly_detection_dashboard(timeframe2)

# Refresh the screen at a configured interval
st_autorefresh(interval=config.dashboard_refresh_interval * 1000, key="anomalyrefresher")
