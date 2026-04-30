# Polygon Stimuli Generator & Experiment Runner

This project is a Python-based tool designed for generating customized polygon stimuli and running automated psychophysical experiments. It allows for precise control over polygon geometry, including vertex stretching, concavity, and texture mapping.

## 🚀 Features

*   **Dynamic Polygon Generation**: Create polygons with any number of vertices.
*   **Target Stretching**: Smoothly control the radius of a specific "target" vertex. 
    *   *Zero-Point Logic*: A "zero" stretch level results in a perfectly flat edge between neighboring vertices.
*   **Concavity Control**: Option to fold a specific vertex inward (concave) independently of the target vertex.
*   **Texture Mapping**: Fill polygons with images from a local database (e.g., CAT2000) using precise masking.
*   **Manual Geometry**: Support for manual entry of radii and angular intervals for complex shapes.
*   **Automated Experiment Runner**: 
    *   Full-screen display using OpenCV.
    *   Reproducible trials using a fixed `random.seed`.
    *   Automatic centering and scaling of stimuli based on screen resolution.

## 🛠 Prerequisites

Ensure you have the following Python libraries installed:
```bash
pip install opencv-python numpy pillow