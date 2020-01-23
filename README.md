# AWS Lambda
## Autoscaling Monitor

### About
Monitors AWS EC2 for Autoscaling events, depending on the type of event, it will either add or remove the instance in question from relevant target groups. Then the function will send a slack message showing the IP and name of the instance. Recently, I have automated the renaming of ec2's. I have begun the process of implementing a REST call to bamboo. In my case, this will kick off a Bamboo job that updates a shared ssh config.

The only dependency this serverless function requires is the `requests` python library. Since Lambda is 'serverless', the dependency must be installed in the same folder as the function `index.py`. I recommend first developing your Lambda scripts locally, then zipping them up and uploading them to your AWS environment for further testing.

### Setup:
1. Create a file named `.pydistutils.cfg` in your home directory. Add the following text, then save it:
```bash
[install]
prefix=
```

2. Go back to your project directory and run:
```sh
pip install request --target .
```
**Delete `.pydistutils.cfg` after you successfully run the above. Otherwise, it will screw up any future pip commands you execute.**

3. Compress all of the files in the project directory into a `.zip` file. Upload the file to a fresh Lambda function.

4. Add your unique environment vars.
```
ARN_TARGET_GROUPS   # a json array of objects of the form {"arn": "abc","port": 123}
BASIC_ACCOUNT_ACCESS_KEY_ID
BASIC_ACCOUNT_SECRET_ACCESS_KEY
SLACK_ENDPOINT
BAMBOO_USERPASS
URL
```
5. Un-Anonymize anything I anonymized.
6. Change the Lambda fnc handler to `index.handler`.
7. Add your function triggers such that the function executes whenever a scaling event occurs.
```json
{
  "detail-type": [
    "EC2 Instance Launch Successful",
    "EC2 Instance Terminate Successful"
  ],
  "source": [
    "aws.autoscaling"
  ],
  "detail": {
    "AutoScalingGroupName": [
      "cluster-worker terraform-xxx"
    ]
  }
}
```
