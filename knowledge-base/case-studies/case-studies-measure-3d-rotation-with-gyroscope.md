# Measure 3D Rotation with Gyroscope - Radixweb

> Read on for how Radixweb built an orthopaedic surgical solution to calculate 3D angles with a 0% failure rate.

**Source:** https://radixweb.com/case-studies/measure-3d-rotation-with-gyroscope

---

# Measure 3D Rotation with Gyroscope

The client is a well-known hip and knee replacement and arthroscopy surgeon based out of Australia. The client prefers to use the most effective surgical techniques and technologies available to orthopaedic surgeons and works to find best suited technology that can be used in surgeries. The main focus here is to not only make the surgery successful but also consider its long term effect in future. It is indeed necessary for every technology used in it should be developed with ~0% failure rate.

The client approached Radix for one of his project that needs to calculate 3D angle in iPhone using gyroscope sensor, to use it in orthopaedic surgery.

## The Problem

The client had theoretical description of the mathematical calculations for “Acetabular Ante version and Inclination” 3D angle for both Radiographic and Anatomical definitions. However, these theories cannot be put to use in providing real life scenario calculations, when we have specific kind of inputs available.

In surgery, the iPhone will be attached and detached with the pelvic as and when required, and based on the 3D rotations (Roll, Tilt and Yaw) of the iPhone, the client wanted to find out the Ante version and Inclination angles of the phone with respect to any lateral and supine position of the patients.

For such calculations, very proficient skillset and amalgamation of both mathematical and cutting edge technology is required. And, this is where Radix made a difference and came up with the solution.

## The Solution

### Excel Sheet Formulas

To provide full proof mathematical calculation, it was important to provide the solution in Excel sheet for mathematical formulas. The calculation is using quaternions to solve 3D rotations.

Once the client confirmed the formulas using his mechanical jigs prepared for testing, we moved to the iOS application implementation using gyroscope. Thus, the mathematical formulas in excel validated our calculations and significantly reduced time required in application development.

### iOS Application

After confirmation of calculations, we worked on the existing iOS application used by the client that had to be enhanced with Ante version and Inclination calculations.

Using the gyroscope sensor of the iPhone and iPad devices, Radix provided set of command buttons based on which the 3d rotation of the iPhone is measured and the angle with respect to patient axis is calculated.

The application also required re-organization of the GUI, so that it can work on all major screen sized iOS devices.

## The Outcome

Radix provided a mathematical calculation and application implementation of it in iOS devices that can be used successfully for orthopedic surgeries. It will result in better success rate of the surgery and reduced future problems for the patients.

Get in Touch

Let’s discuss your project and build something extraordinary

Start Conversation