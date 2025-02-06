import boto3

ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    print("### Lambda execution started ###")
    print(f"Event received: {event}")
    
    instance_id = event.get('instance_id')
    action = event.get('action')
    
    # Validate event parameters
    if not instance_id or not action:
        print(f"Missing required parameters: instance_id={instance_id}, action={action}")
        return {
            "statusCode": 400,
            "body": "Missing required parameters: 'instance_id' and 'action' are required."
        }
    
    print(f"Processing instance: {instance_id}, action: {action}")
    
    try:
        # Retrieve the tags for the instance
        print(f"Fetching tags for instance: {instance_id}")
        instance = ec2.describe_instances(InstanceIds=[instance_id])
        tags = {tag['Key']: tag['Value'] for tag in instance['Reservations'][0]['Instances'][0].get('Tags', [])}
        print(f"Tags for instance {instance_id}: {tags}")
        
        # Check if schedule_enabled tag is set to 'true'
        if tags.get('schedule_enabled') != 'true':
            print(f"Action '{action}' skipped for instance {instance_id}. 'schedule_enabled' tag is not set to 'true'.")
            return {
                "statusCode": 400,
                "body": f"Action '{action}' not allowed for instance {instance_id}. 'schedule_enabled' tag is not set to 'true'."
            }
        
        # Perform the requested action
        if action == 'start':
            print(f"Attempting to start instance: {instance_id}")
            ec2.start_instances(InstanceIds=[instance_id])
            print(f"Successfully started instance: {instance_id}")
            return {
                "statusCode": 200,
                "body": f"Successfully started instance {instance_id}"
            }
        elif action == 'stop':
            print(f"Attempting to stop instance: {instance_id}")
            ec2.stop_instances(InstanceIds=[instance_id])
            print(f"Successfully stopped instance: {instance_id}")
            return {
                "statusCode": 200,
                "body": f"Successfully stopped instance {instance_id}"
            }
        else:
            print(f"Invalid action '{action}' received for instance {instance_id}")
            return {
                "statusCode": 400,
                "body": f"Invalid action '{action}'. Allowed actions are 'start' and 'stop'."
            }
    except Exception as e:
        print(f"Error occurred while processing instance {instance_id} with action '{action}': {e}")
        return {
            "statusCode": 500,
            "body": f"An error occurred while performing '{action}' on instance {instance_id}: {e}"
        }
    finally:
        print("### Lambda execution completed ###")
