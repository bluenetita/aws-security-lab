# Wazuh integration status

A dedicated AWS EC2 instance was allocated to Wazuh, but **no Wazuh-to-BlueGuard data ingestion or detection correlation has been validated in this project**.

This directory does not contain working deployment artifacts for an integrated Wazuh Manager. Previous experiments in other laboratory environments are outside the scope of this repository; they are not automatically reusable in AWS.

Future work: secure ingestion of Wazuh events, explicit parsing/detection rules, evidence-based Zeek/endpoint correlation, tenant separation and production retention policies. Avoid presenting synthetic dashboard alerts as Wazuh detections.
