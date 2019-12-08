# aws-autoscaling-monitor
Monitors AWS EC2 for Autoscaling events, depending on the type of event, it will either add or remove the instance in question from relevant target groups.

New features (still a work in progress) will rename all of the tag names in AWS for the autoscaling instances and send an API call to Bamboo to kick off another script that updates our shared ssh configs.
