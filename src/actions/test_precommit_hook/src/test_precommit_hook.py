def lambda_handler(event, context):
    number = event.get('number', 0)

    print("processing number: " + str(number))

    if not type(number) is int:
        return {
            "statusCode": 400,
            "body": "Error: 'number' must be an integer."
        }
    
    with open("log.txt", 'w') as file:
        file.write("Processing number: " + str(number) + "\n")

    try:
        result = factorial(number)
    except ValueError as e:
        return {
            "StatusCode": 400,
            "body": str(e)
        }

    return {
        "StatusCode": 200,
        "body": {
            "number": number,
            "factorial": result
        }
    }

def factorial(n:int) -> int:
    if n ==0 or n==1:
        return 1
    
    return n * factorial(n-1)