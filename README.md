# Squash Court Availability Checker

A Python script that checks squash court availability at Alfreton Leisure Centre via the Places Leisure OpenActive API. It checks both the requested time slot and the 40-minute period before it, providing clean JSON output with booking URLs.

## Features

- **Real-time availability checking** via Places Leisure OpenActive API
- **40-minute slot validation** (standard squash court duration)
- **Automatic date handling** - defaults to today if no date provided
- **Clean JSON output** - perfect for automation and integration
- **Dynamic booking URLs** - includes proper time parameters
- **API limitation handling** - gracefully handles incomplete data

## Installation

1. Clone or download the script
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Check availability for today at 12:00
python check_squash_availability.py --start-time 12:00

# Check availability for specific date and time
python check_squash_availability.py --date 2026-02-04 --start-time 15:20
```

### Parameters

- `--date` (optional): Target date in YYYY-MM-DD format. Defaults to today if not provided
- `--start-time` (required): Start time in HH:MM format

## Output Format

The script returns clean JSON with the following structure:

```json
{
  "success": true,
  "message": "There is one slot free before your booking",
  "main_slot_available": 1,
  "before_slot_available": 1,
  "booking_url": "https://placesleisure.gladstonego.cloud/book/calendar/041A000005?activityDate=2026-02-03T11:20:00.000Z&previousActivityDate=2026-02-03T10:40:00.000Z"
}
```

### Response Fields

- `success`: Boolean indicating if slots are available before your booking time
- `message`: Human-readable message about availability
- `main_slot_available`: Number of available courts in your requested time slot
- `before_slot_available`: Number of available courts in the 40 minutes before your slot
- `booking_url`: Direct link to booking calendar with proper time parameters

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
5. **Returns clean JSON** with availability status and booking URL

## API Limitations

The OpenActive API sometimes provides incomplete data for partially booked scenarios. When this occurs:

- The script shows generic availability counts instead of specific court assignments
- The booking URL allows users to check exact court availability on the website
- No misleading assumptions are made about which specific court is available

## Examples

### Check Today's Availability
```bash
python check_squash_availability.py --start-time 10:00
```

### Check Future Date
```bash
python check_squash_availability.py --date 2026-02-10 --start-time 18:00
```

### Integration Example
```bash
# Use in scripts for automation
RESULT=$(python check_squash_availability.py --start-time 14:00)
AVAILABLE=$(echo $RESULT | jq -r '.before_slot_available')

if [ "$AVAILABLE" -gt 0 ]; then
    echo "Slots available! Check booking URL for details."
    echo $RESULT | jq -r '.booking_url'
else
    echo "No slots available before your requested time."
fi
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
