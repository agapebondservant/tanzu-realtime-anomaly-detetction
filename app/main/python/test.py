import streamlit as st
import matplotlib.pyplot as plt

# create your figure and get the figure object returned
fig = plt.figure()
plt.plot([1, 2, 3, 4, 5])

st.pyplot(fig)