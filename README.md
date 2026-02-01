🚁 OAK-D Real-Time Monitoring Dashboard

A full-stack web dashboard for real-time monitoring of UAV sensor data and AI vision detections using an OAK-D.

This system streams live telemetry and computer vision results to a browser over a local network, allowing users to monitor environmental conditions and visual detections in real time.

🎥 Demo Video

[![Watch the demo](demo-thumbnail.png)](https://drive.google.com/drive/folders/1oNYpHxRfkSwBWmsYMtoZCQdEKQsBif0u?usp=drive_link)


What the demo shows

Real-time sensor data updating in dashboard charts

Live camera feed from the laptop device as a example

AI detection working in real time (tested using a human face)

Smooth, dynamic updates without page refresh

📌 Overview

This project implements a real-time monitoring interface that visualizes data collected from onboard UAV sensors and AI vision systems.

The dashboard displays:

🌡 Temperature

💧 Humidity

🌬 Gas sensor readings

📍 UAV coordinates (x, y, z)

📷 Live camera feed

🎯 AI detections (e.g., faces, markers, objects)

All data updates dynamically and can be logged for later review.

👥 Project Context

Developed as part of a collaborative engineering project to build a real-time UAV sensor and vision monitoring platform.

My role focused on the software system, including:

Backend API development

Sensor data processing and formatting

Integration of AI detection outputs

Frontend dashboard logic and visualization

Enabling real-time communication between hardware and the web interface

🏗 System Architecture
4

Data Flow:
Sensors + OAK-D → Python Backend → API → React Frontend → Web Browser

Backend

Built using Flask
Handles:

Sensor data ingestion

AI detection data

REST API endpoints

Data logging

Frontend

Built using React
Displays:

Live charts

Sensor values

Detection information

System status

🖥 Key Features

✔ Real-time environmental sensor monitoring
✔ Live AI vision detection feed
✔ UAV position tracking
✔ Dynamic dashboard updates
✔ Historical data logging
✔ Accessible over local network

🛠 Tech Stack

Layer	Technology
Backend	 = Python, Flask

Frontend =	React, JavaScript, HTML, CSS

Vision =	OAK-D (DepthAI)

Data =	Environmental sensors + AI detections

Network = 	Local web server (LAN access)

▶ How to Run

1️⃣ Backend Setup
pip install -r requirements.txt
python app.py

2️⃣ Frontend Setup
npm install
npm start

3️⃣ Open Dashboard

Go to:

http://<your-local-ip>:3000
