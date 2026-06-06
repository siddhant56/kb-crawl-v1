# DevSecOps Case Study: Reducing Downtime & Bugs Efficiently

> Radixweb's DevSecOps approach using Azure DevOps, static code analysis, and vulnerability scanning led to <1% downtime and a 95% reduction in bugs.

**Source:** https://radixweb.com/case-studies/devsecops-implementation-case-study

---

## About the Client

SynCore is a SaaS company that owns a pricing-based software platform for managing RFx processes, which include requests for information, proposals, and quotes. Their software helps businesses efficiently handle these tasks by automating the process of collecting and evaluating bids.

## The Problem

The client team’s existing setup was mostly manual, with only an automated proof of concept (PoC) pipeline in place. They used Bitbucket for DevOps, but their deployment process was very inconvenient to manage. It depended on version control systems and updates the local branch on a virtual machine without proper packaging or version control.

Essentially, the entire process was like working on a local computer - a branch is pulled to a VM, updated, and then refreshed using PM2 and Nginx to apply changes without downtime. On top of this, database changes had to be shared through Slack, which is not very organized or efficient.

## Initial Needs and Challenges

They were already working on a DevOps transformation and wanted to integrate security earlier in the process. Our role was to help them build a team with the processes and technologies needed to achieve that goal.

Dhaval Dave

VP – Operations and Delivery

## What We Proposed

Build Innovative Software Products with Security as a Top Priority.

Let Us Help

## Solutions to be Implemented

We recommended using 80 hours a month for March 2022 to set up the required processes and run some pilot tests. From April 2022, we managed and monitored the process effectively. Here are the strategies we implemented:

### Accessibility Features

To achieve the desired process, we used Azure DevOps services with a server agent for builds and deployments. CI/CD and test pipelines were set up with telemetry-based monitoring and anomaly detection, while Firebase Hosting supported the Angular front end. Azure DevOps is secure, enterprise-ready, and enables data-driven insights via its marketplace, while Firebase delivers cost-effective, automated CDN support.

### Static Code Analysis

We’ll integrate static code analyzers to help the client team write secure code that forms the architectural backbone of the system. Static Application Security Testing (SAST) tools like SonarQube and TSLint or any tool of their choice would work as an automated part of their development process and help detect and fix potential vulnerabilities early. The setup will be a one-time activity for our team.

### Vulnerability Scan

Security testing solutions will be implemented into the development process to check for security issues throughout the CI/CD pipeline. The team can check the code for bugs and vulnerabilities before it’s released. We’ll set up an OWASP recommended tool for this, and it will be a one-time setup as well.

### Unit Tests/Penetration Tests

The client team can write tests to check individual parts of the code. We have set up a test pipeline to automate running these tests with each build. Hence, they can check everything before releasing new versions. Our team will handle the setup for this, which will be done just once.

### Compliance Testing

In DevSecOps, compliance is about continuously managing and fixing security settings in real time. Instead of just ticking boxes, we’ve made sure they get alerts when any security settings change. This task is optional, and our team can handle it if needed.

### Deployment Pipeline

Our team will manage the process of deploying the final build to the production environment. This involves handling various types of build outputs, such as libraries and bundles. Our team will set up the deployment process once, and their development team will trigger the deployments using this setup.

<7 Hours

of Downtime in 720 Hours in a Month (1%)

2-3

Security Incidents Cut from 10 per Quarter (-82%)

10+ times

New Build a month Instead of 4 (+57%)

The transformation from DevOps to DevSecOps was absolutely critical for our product and team. All we were looking for was an experienced team to help us set the path and get our hands on the process. Radixweb did it so. Everyone is happy with the workflow and our clients hardly come up with major issues.

David Barnett

COO

Work with a Team That Puts Security Front-and-Centre in Software Development

Connect Now

We're offline

Leave a message

 __