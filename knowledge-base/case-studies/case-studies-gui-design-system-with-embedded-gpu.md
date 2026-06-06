# GUI Design System with Embedded GPU - Radixweb

> Low-cost hardware was developed to drive the Client's LCD touch panels, as well as an open source library (C/C++) to generate the GUI on the screen.

**Source:** https://radixweb.com/case-studies/gui-design-system-with-embedded-gpu

---

# GUI Design System with Embedded GPU

The client is a globally leading manufacturer for information display systems including: Liquid Crystal Display, Touch Screens, TFT, OLED, LCD etc.

The client wanted to develop a system for their LCD touch screens; wherein the user can design GUI online and use this design- WYSIWYG on their LCD touch screens. The requirement was to develop low cost hardware to drive their LCD touch screens and open source library (C/C++) to render GUI on the screen.

## The Problem

This project included combination of diverse technologies like web development, hardware development, and firmware development for the hardware with below mentioned feature requirements:

### Website:

  * User friendly GUI designing editor with library of royalty free images.
  * Design editor with multi layers architecture with image transparency and alpha blending mechanism.
  * The SDK configuration also includes Eclipse IDE with PHP Plug-in, Open Office, Apache, Subversion and is also integrated with the domain controller
  * Other standard features like user management, company management, etc.

The requirement also included development of firmware flashing and desktop emulator applications to put data on hardware and access hardware using protocols.

### Hardware development:

  * Low cost.
  * With interfaces like USB, SPI, Serial port, GPIO etc.
  * i2c connection for client’s touch panel.
  * o LCD screen connector to drive LCD.

The requirement also included development of firmware flashing and desktop emulator applications to put data on hardware and access hardware using protocols.

### Firmware development:

  * Graphic rendering logic with multiple layer for rendering image, text, animation, etc.
  * Protocols to communicate with other devices.
  * The board should boot fast.

The requirement also included development of firmware flashing and desktop emulator applications to put data on hardware and access hardware using protocols.

## The Solution

We developed emulator application which communicates with hardware using USB-OTG port which is detected as serial port on PC. PC and hardware uses custom defined protocol/commands for communication. We also developed firmware flashing application which uses JTAG or USB to transfer firmware into the NAND flash of board.

## The Outcome

Get in Touch

Let’s discuss your project and build something extraordinary

Start Conversation

We're offline

Leave a message

 __