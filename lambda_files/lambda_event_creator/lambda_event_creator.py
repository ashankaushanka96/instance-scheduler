import boto3
import json
from datetime import datetime, timezone
from croniter import croniter  # Requires `croniter` library

ec2 = boto3.client('ec2')
events = boto3.client('events')

def lambda_handler(event, context):
    print("################################ Lambda execution started ################################")
    try:
        # Retrieve instances with relevant tags
        print("Fetching EC2 instances with scheduling tags...")
        instances = ec2.describe_instances(
            Filters=[
                {'Name': 'tag-key', 'Values': ['start_time', 'stop_time', 'start_time_*', 'stop_time_*']}
            ]
        )
        print(f"Fetched {len(instances['Reservations'])} reservations with scheduling tags.")
        
        # Delete existing scheduler events
        print("Deleting existing scheduler events...")
        delete_instance_scheduler_events()
        
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                print(f"Processing instance: {instance_id}")
                tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                print(f"Tags for instance {instance_id}: {tags}")
                
                # Initialize flag to track scheduled events
                event_scheduled = False
                
                # Process single start_time and stop_time tags
                if 'start_time' in tags:
                    print(f"Scheduling start event for instance {instance_id} with tag 'start_time'.")
                    if schedule_event_today(instance_id, tags['start_time'], 'start', 'start_time'):
                        event_scheduled = True
                if 'stop_time' in tags:
                    print(f"Scheduling stop event for instance {instance_id} with tag 'stop_time'.")
                    if schedule_event_today(instance_id, tags['stop_time'], 'stop', 'stop_time'):
                        event_scheduled = True
                
                # Process multiple start_time_* and stop_time_* tags
                for key, value in tags.items():
                    if key.startswith('start_time_'):
                        print(f"Scheduling start event for instance {instance_id} with tag '{key}'.")
                        if schedule_event_today(instance_id, value, 'start', key):
                            event_scheduled = True
                    elif key.startswith('stop_time_'):
                        print(f"Scheduling stop event for instance {instance_id} with tag '{key}'.")
                        if schedule_event_today(instance_id, value, 'stop', key):
                            event_scheduled = True
                
                # Add 'schedule_enabled' tag if at least one event was successfully scheduled
                if event_scheduled and 'schedule_enabled' not in tags:
                    try:
                        print(f"Adding 'schedule_enabled' tag to instance {instance_id}.")
                        ec2.create_tags(
                            Resources=[instance_id],
                            Tags=[{'Key': 'schedule_enabled', 'Value': 'true'}]
                        )
                        print(f"Tag 'schedule_enabled' successfully added to instance {instance_id}.")
                    except Exception as e:
                        print(f"Error adding 'schedule_enabled' tag to instance {instance_id}: {e}")
                elif event_scheduled:
                    print(f"Tag 'schedule_enabled' already exists for instance {instance_id}.")
        
        print("### Lambda execution completed successfully ###")
        return {"statusCode": 200, "body": "One-time events created for today's schedules"}
    except Exception as e:
        print(f"Error during Lambda execution: {e}")
        return {"statusCode": 500, "body": "Error creating one-time events"}

def delete_instance_scheduler_events():
    prefix = "instance-scheduler"
    try:
        print(f"Fetching EventBridge rules with prefix '{prefix}'...")
        rules = events.list_rules(NamePrefix=prefix)
        print(f"Found {len(rules['Rules'])} rules with prefix '{prefix}'.")

        for rule in rules['Rules']:
            rule_name = rule['Name']
            print(f"Deleting targets and rule: {rule_name}")
            
            # Remove all targets from the rule
            targets = events.list_targets_by_rule(Rule=rule_name)
            target_ids = [target['Id'] for target in targets['Targets']]
            if target_ids:
                events.remove_targets(Rule=rule_name, Ids=target_ids)
                print(f"Removed targets from rule: {rule_name}")
            
            # Delete the rule
            events.delete_rule(Name=rule_name)
            print(f"Deleted rule: {rule_name}")
        
        print("All instance-scheduler events deleted successfully.")
    except Exception as e:
        print(f"Error deleting events: {e}")

def schedule_event_today(instance_id, cron_expression, action, tag_key):
    print(f"################### Scheduling event for instance: {instance_id}, tag: {tag_key}, action: {action}, cron_expression: {cron_expression}")
    current_time = datetime.now(timezone.utc)
    
    # Validate cron expression
    try:
        cron = croniter(cron_expression, current_time)
        next_run = cron.get_next(datetime)  # Get the next run time as a datetime object
    except Exception as e:
        print(f"Invalid cron expression {cron_expression}: {str(e)}")
        return False
    
    print(f"Next run for cron expression {cron_expression}: {next_run}")
    
    # Parse allowed days from the cron expression
    cron_parts = cron_expression.split()
    if len(cron_parts) < 5:
        print(f"Invalid cron expression {cron_expression}: Missing parts.")
        return False
    
    allowed_days = cron_parts[4]  # 5th part specifies days of the week
    if allowed_days != '*':
        allowed_days = set(
            int(day) for day in allowed_days.split(',') if '-' not in day
        ) | set(
            day for r in allowed_days.split(',') if '-' in r
            for day in range(int(r.split('-')[0]), int(r.split('-')[1]) + 1)
        )
    else:
        allowed_days = set(range(7))  # All days (0-6 for Sunday to Saturday)
    
    next_run_weekday = int(next_run.strftime('%w'))
    if next_run_weekday not in allowed_days:
        print(f"Skipping event for {tag_key}: Next run day {next_run_weekday} is not allowed.")
        return False
    
    if next_run.date() != current_time.date():
        print(f"Skipping event for {tag_key}: Not scheduled for today. Next run: {next_run.date()}.")
        return False

    rule_name = f"instance-scheduler-{instance_id}-{tag_key}"
    target_id = f"instance-scheduler-target-{instance_id}-{tag_key}"
    target_arn = f"arn:aws:lambda:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity().get('Account')}:function:lambda-ec2-start-stop"  # Replace with actual Lambda function name

    schedule_expression = next_run.strftime("cron(%M %H %d %m ? %Y)")
    print(f"Creating EventBridge rule: {rule_name} with schedule: {schedule_expression}")
    
    try:
        # Create EventBridge rule
        events.put_rule(
            Name=rule_name,
            ScheduleExpression=schedule_expression,
            State='ENABLED'
        )
        print(f"Created rule: {rule_name}")

        # Add target to the rule
        events.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': target_id,
                    'Arn': target_arn,
                    'Input': json.dumps({'instance_id': instance_id, 'action': action, 'tag_key': tag_key})
                }
            ]
        )
        print(f"Added target to rule: {rule_name}")
        return True
    except Exception as e:
        print(f"Error scheduling event for {tag_key}: {e}")
        return False
