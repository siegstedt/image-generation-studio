import base64
import http.client
import json
import os
import time
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# Load environment variables from the .env file
load_dotenv()

# App Title
st.set_page_config(page_title="Image Generation Studio", layout="wide")

st.title("Image Generation Studio")

# Sidebar for parameters
st.sidebar.header("Image Generation Parameters")

# Fetch API key from .env if available
api_key = os.getenv("API_KEY")

# If API key is not found in .env, prompt the user for input
if not api_key:
    api_key = st.sidebar.text_input("Enter your API Key", type="password")

# Ensure the API key is provided
if not api_key:
    st.sidebar.error("Please provide an API key to generate images.")
else:
    st.sidebar.success("API key loaded.")


# Image generation parameters
prompt = st.sidebar.text_area("Prompt", value="ein fantastisches bild")
width = st.sidebar.slider(
    "Width (pixels)", min_value=256, max_value=1440, value=1024, step=32
)
height = st.sidebar.slider(
    "Height (pixels)", min_value=256, max_value=1440, value=768, step=32
)
steps = st.sidebar.slider("Steps", min_value=1, max_value=50, value=28)
prompt_upsampling = st.sidebar.checkbox("Prompt Upsampling", value=False)
seed = st.sidebar.number_input("Seed (optional)", value=42, step=1)
guidance = st.sidebar.slider("Guidance", min_value=1.5, max_value=5.0, value=3.0)
safety_tolerance = st.sidebar.slider(
    "Safety Tolerance", min_value=0, max_value=6, value=2
)

# Button to trigger image generation
generate_image = st.sidebar.button("Generate Image")

# Initialize Session State for task_id if not already set
if "task_id" not in st.session_state:
    st.session_state.task_id = None


# Function to call the Flux.1 API
def generate_image_from_api(
    prompt,
    width,
    height,
    steps,
    prompt_upsampling,
    seed,
    guidance,
    safety_tolerance,
    api_key,
):
    conn = http.client.HTTPSConnection("api.bfl.ml")

    payload = json.dumps(
        {
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "prompt_upsampling": prompt_upsampling,
            "seed": seed,
            "guidance": guidance,
            "safety_tolerance": safety_tolerance,
        }
    )

    headers = {
        "Content-Type": "application/json",
        "X-Key": api_key,  # Use the API key provided
    }

    conn.request("POST", "/v1/flux-dev", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))


# Function to get the image generation result using the task id
def get_image_result(task_id):
    conn = http.client.HTTPSConnection("api.bfl.ml")

    # Make a GET request to retrieve the result by task id
    conn.request("GET", f"/v1/get_result?id={task_id}")
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))


# Main content area for showing the result
if generate_image:
    # Fetch generated image from API
    result = generate_image_from_api(
        prompt,
        width,
        height,
        steps,
        prompt_upsampling,
        seed,
        guidance,
        safety_tolerance,
        api_key,
    )

    if "id" in result:
        task_id = result["id"]

        # Store the task_id in session state
        st.session_state.task_id = task_id


# If task_id is available in session state, retrieve the image result
if st.session_state.task_id:
    task_id = st.session_state.task_id

    # Display the task ID
    st.info(f"Image generation started. Task ID: {task_id}")

    # Poll for the result with a delay
    status = "Pending"
    while status == "Pending":
        time.sleep(5)  # Polling interval
        result_status = get_image_result(task_id)
        status = result_status.get("status", "Error")
        st.write(f"Current status: {status}")

        if status == "Ready":
            image_url = result_status["result"]["sample"]
            st.image(image_url, caption="Generated Image", use_column_width=True)

            # Option to download the image
            st.markdown(f"[Download Image]({image_url})", unsafe_allow_html=True)
            break
        elif status in ["Request Moderated", "Content Moderated", "Error"]:
            st.error(f"Failed to generate image. Status: {status}")
            break
