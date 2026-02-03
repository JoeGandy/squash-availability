# Squash Court Availability Checker

A Python script that checks squash court availability at Alfreton Leisure Centre via the Places Leisure OpenActive API. It checks both the requested time slot and the 40-minute period before it, providing both command-line JSON output and a programmatic interface for integration.

## Features

- **Real-time availability checking** via Places Leisure OpenActive API
- **40-minute slot validation** (standard squash court duration)
- **Automatic date handling** - defaults to today if no date provided
- **Clean JSON output** - perfect for automation and integration
- **Programmatic interface** - structured data return for Python integration
- **Dynamic booking URLs** - includes proper time parameters
- **API limitation handling** - gracefully handles incomplete data
- **Detailed court information** - returns full court data for advanced usage

## Installation

1. Clone or download the script
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
# Check availability for today at 12:00
python check_squash_availability.py --start-time 12:00

# Check availability for specific date and time
python check_squash_availability.py --date 2026-02-04 --start-time 15:20
```

### Programmatic Interface

```python
from check_squash_availability import check_availability_programmatic

# Check availability programmatically
result = check_availability_programmatic("2026-02-04", "15:20")

if result["success"]:
    print(f"Available slots before booking: {result['before_slot_available']}")
    print(f"Booking URL: {result['booking_url']}")
    print(f"Main slot available: {result['main_slot_available']}")
else:
    print(f"No slots available: {result['message']}")
```

### Parameters

- `--date` (optional): Target date in YYYY-MM-DD format. Defaults to today if not provided
- `--start-time` (required): Start time in HH:MM format

## Output Format

### Command Line JSON Output

```json
{
  "success": true,
  "message": "There is one slot free before your booking",
  "main_slot_available": 1,
  "before_slot_available": 1,
  "booking_url": "https://placesleisure.gladstonego.cloud/book/calendar/041A000005?activityDate=2026-02-03T11:20:00.000Z&previousActivityDate=2026-02-03T10:40:00.000Z"
}
```

### Programmatic Interface Return

The `check_availability_programmatic()` function returns a structured dictionary with additional detailed information:

```python
{
    "success": bool,
    "message": str,
    "main_slot_available": int,
    "before_slot_available": int,
    "booking_url": str,
    "main_court_info": Dict,  # Detailed court availability for main slot
    "before_court_info": Dict,  # Detailed court availability for before slot
    "time_slots": {
        "main": {"start": str, "end": str},
        "before": {"start": str, "end": str}
    }
}
```

### Response Fields

- `success`: Boolean indicating if slots are available before your booking time
- `message`: Human-readable message about availability
- `main_slot_available`: Number of available courts in your requested time slot
- `before_slot_available`: Number of available courts in the 40 minutes before your slot
- `booking_url`: Direct link to booking calendar with proper time parameters
- `main_court_info`: Detailed court information for the main slot (programmatic only)
- `before_court_info`: Detailed court information for the before slot (programmatic only)
- `time_slots`: Time range information for both slots (programmatic only)

### Message Types

- `"There is one slot free before your booking"` - Success with 1 available slot
- `"There are X slots free before your booking"` - Success with multiple available slots
- `"There is no slots free before your booking"` - No slots available

## How It Works

1. **Fetches all slot data** from Places Leisure OpenActive API using RPDE pagination
2. **Filters for Alfreton squash courts** (facility ID: 041A000005)
3. **Analyzes two time periods**:
   - Your requested slot (40 minutes)
   - The 40 minutes before your slot
4. **Handles API limitations** gracefully when specific court data is incomplete
5. **Returns structured data** with availability status and booking URL

## API Limitations

The OpenActive API sometimes provides incomplete data for partially booked scenarios. When this occurs:

- The script shows generic availability counts instead of specific court assignments
- The booking URL allows users to check exact court availability on the website
- No misleading assumptions are made about which specific court is available

## Examples

### Command Line Usage
```bash
# Check today's availability
python check_squash_availability.py --start-time 10:00

# Check future date
python check_squash_availability.py --date 2026-02-10 --start-time 18:00
```

### Python Integration
```python
from check_squash_availability import check_availability_programmatic

# Check availability and get detailed court information
result = check_availability_programmatic("2026-02-04", "15:20")

# Access detailed court information
for court_name, court_data in result["before_court_info"].items():
    if court_data["available"]:
        print(f"Available: {court_name} - {court_data['remaining_uses']} slots")
        
# Access time slot information
print(f"Before slot: {result['time_slots']['before']['start']}-{result['time_slots']['before']['end']}")
print(f"Main slot: {result['time_slots']['main']['start']}-{result['time_slots']['main']['end']}")
```

### Advanced Integration
```python
from check_squash_availability import check_availability_programmatic
import datetime

def find_available_slots(date, start_times):
    """Find available slots for multiple time periods"""
    available_slots = []
    
    for time in start_times:
        result = check_availability_programmatic(date, time)
        
        if result["success"] and result["before_slot_available"] > 0:
            available_slots.append({
                "time": time,
                "before_available": result["before_slot_available"],
                "main_available": result["main_slot_available"],
                "booking_url": result["booking_url"]
            })
    
    return available_slots

# Example: Check multiple times
times_to_check = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
available = find_available_slots("2026-02-04", times_to_check)

for slot in available:
    print(f"Available at {slot['time']}: {slot['before_available']} slots before, {slot['main_available']} during")
```

## Requirements

- Python 3.7+
- requests
- argparse
- datetime

## Target Facility

**Alfreton Leisure Centre**
- Facility ID: 041A000005
- Courts: Squash Court 1 & Squash Court 2
- Slot Duration: 40 minutes

## License

This script is provided as-is for checking squash court availability at Places Leisure facilities.
