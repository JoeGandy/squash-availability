#!/usr/bin/env python3
"""
Squash Court Availability Checker for Places Leisure

This script specifically checks squash court availability at Places Leisure facilities.
It checks 40-minute slots and the 40 minutes before each slot.

Usage:
    python check_squash_availability.py --date 2026-02-03 --start-time 10:00
"""

import sys
import requests
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class PlacesLeisureAPI:
    """Interface to the Places Leisure OpenActive API"""
    
    BASE_URL = "https://opendata.leisurecloud.live/api/feeds/PlacesLeisure-live-slots"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SquashCourtChecker/1.0'
        })
    
    def fetch_slots(self, after_url: Optional[str] = None) -> Dict:
        """Fetch slots from the API"""
        url = after_url or self.BASE_URL
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching slots: {e}")
            sys.exit(1)
    
    def fetch_all_slots(self) -> List[Dict]:
        """Fetch all slots by following RPDE pagination properly"""
        all_slots = []
        next_url = None
        page_count = 0
        
        while True:
            data = self.fetch_slots(next_url)
            page_count += 1
            
            # Add slots to our collection
            if 'items' in data:
                all_slots.extend(data['items'])
            
            # Check if we've reached the last page according to RPDE spec:
            # Last page has empty items array AND next matches current URL
            current_url = next_url or self.BASE_URL
            next_page_url = data.get('next')
            
            if (not data.get('items') or len(data.get('items', [])) == 0) and next_page_url == current_url:
                break
            
            # Get next page URL
            next_url = next_page_url
            if not next_url:
                break
                
            # Safety check to prevent infinite loops
            if page_count > 1000:
                print(f"Warning: Stopped after {page_count} pages to prevent infinite loop")
                break
        
        return all_slots

class SquashAvailabilityChecker:
    """Main class for checking squash court availability"""
    
    def __init__(self):
        self.api = PlacesLeisureAPI()
    
    def parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into datetime object"""
        try:
            return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError as e:
            print(f"Error parsing datetime: {e}")
            sys.exit(1)
    
    def time_overlaps(self, slot_start: datetime, slot_end: datetime, 
                     check_start: datetime, check_end: datetime) -> bool:
        """Check if two time periods overlap"""
        return (slot_start < check_end) and (slot_end > check_start)
    
    def filter_squash_slots_by_time(self, slots: List[Dict], target_date: str, 
                                   start_time: str, end_time: str) -> List[Dict]:
        """Filter squash slots by target date and time range"""
        target_start = self.parse_datetime(target_date, start_time)
        target_end = self.parse_datetime(target_date, end_time)
        
        # Squash facility identifier for Alfreton Leisure Centre
        squash_facility_ids = [
            "041A000005"   # Alfreton Leisure Centre Squash
        ]
        
        filtered_slots = []
        
        for slot_item in slots:
            slot_data = slot_item.get('data', {})
            if not slot_data:
                continue
            
            # Check if this is a squash facility by facilityUse identifier
            facility_use = slot_data.get('facilityUse', '')
            is_squash = any(facility_id in facility_use for facility_id in squash_facility_ids)
            
            if not is_squash:
                continue
            
            # Parse slot start and end times
            try:
                slot_start = datetime.fromisoformat(slot_data['startDate'].replace('Z', '+00:00'))
                slot_end = datetime.fromisoformat(slot_data['endDate'].replace('Z', '+00:00'))
                
                # Ensure target_start has timezone info for comparison
                if target_start.tzinfo is None:
                    target_start = target_start.replace(tzinfo=slot_start.tzinfo)
                if target_end.tzinfo is None:
                    target_end = target_end.replace(tzinfo=slot_end.tzinfo)
                
                # Check if slot is on the target date and overlaps with target time
                if (slot_start.date() == target_start.date() and 
                    self.time_overlaps(slot_start, slot_end, target_start, target_end)):
                    filtered_slots.append(slot_item)
                    
            except (KeyError, ValueError) as e:
                continue
        
        return filtered_slots
    
    def get_squash_court_availability(self, slots: List[Dict]) -> Dict[str, Dict]:
        """Get availability information for squash courts - handles individual court slots"""
        court_info = {}
        
        # Squash facility identifier for Alfreton Leisure Centre
        squash_facility_ids = [
            "041A000005"   # Alfreton Leisure Centre Squash
        ]
        
        # Group slots by time to identify individual court slots
        time_slots = {}
        
        for slot_item in slots:
            slot_data = slot_item.get('data', {})
            if not slot_data:
                continue
            
            # Get facility information
            facility_use = slot_data.get('facilityUse', '')
            
            # Extract facility ID from URL
            facility_id = facility_use.split('/')[-1] if '/' in facility_use else facility_use
            
            # Only include squash facilities
            if facility_id not in squash_facility_ids:
                continue
            
            # Group by start time to find individual court slots
            start_time = slot_data.get('startDate', '')
            if start_time not in time_slots:
                time_slots[start_time] = []
            
            time_slots[start_time].append(slot_data)
        
        # Process each time group to assign courts to individual slots
        for start_time, slot_group in time_slots.items():
            if len(slot_group) == 1:
                # Single slot - could be both courts together or one court
                self._process_single_slot(slot_group[0], court_info)
            else:
                # Multiple slots at same time - these are individual court slots
                self._process_multiple_court_slots(slot_group, court_info)
        
        return court_info
    
    def _process_single_slot(self, slot_data: Dict, court_info: Dict):
        """Process a single slot (could be both courts together or one court)"""
        locations = slot_data.get('beta:sportsActivityLocation', [])
        remaining_uses = slot_data.get('remainingUses', 0)
        offers = slot_data.get('offers', [])
        
        # Check if this is a partially booked scenario (one court available, one booked)
        # This happens when we have 1 slot with remaining: 0 but price: 10.25
        # The missing slot would have remaining: 1 and price: 0
        is_partially_booked = (remaining_uses == 0 and 
                               len(offers) > 0 and 
                               offers[0].get('price', 0) > 0)
        
        if not locations:
            # No location info - treat as facility level
            court_name = f"Squash Court ({slot_data.get('identifier', 'Unknown')})"
            court_id = slot_data.get('identifier', 'Unknown')
            
            if court_name not in court_info:
                court_info[court_name] = {
                    'id': court_id,
                    'available': False,
                    'remaining_uses': 0,
                    'slots': []
                }
            
            # Update availability
            court_info[court_name]['remaining_uses'] = max(
                court_info[court_name]['remaining_uses'], remaining_uses
            )
            
            if remaining_uses > 0:
                court_info[court_name]['available'] = True
            
            court_info[court_name]['slots'].append({
                'start': slot_data.get('startDate'),
                'end': slot_data.get('endDate'),
                'remaining': remaining_uses
            })
        else:
            # Process each court location (fallback for single slots)
            for location in locations:
                location_name = location.get('name', '')
                location_id = location.get('identifier', '')
                
                if isinstance(location_name, str) and location_name:
                    court_name = location_name
                else:
                    court_name = f"Squash Court ({location_id})"
                
                court_id = location_id or slot_data.get('identifier', 'Unknown')
                
                if court_name not in court_info:
                    court_info[court_name] = {
                        'id': court_id,
                        'available': False,
                        'remaining_uses': 0,
                        'slots': []
                    }
                
                # Update availability
                court_info[court_name]['remaining_uses'] = max(
                    court_info[court_name]['remaining_uses'], remaining_uses
                )
                
                if remaining_uses > 0:
                    court_info[court_name]['available'] = True
                
                court_info[court_name]['slots'].append({
                    'start': slot_data.get('startDate'),
                    'end': slot_data.get('endDate'),
                    'remaining': remaining_uses
                })
        
        # Handle partially booked scenario - create the missing slot
        if is_partially_booked and len(locations) == 2:
            # The missing slot should have remaining: 1 and price: 0
            missing_slot_data = {
                'startDate': slot_data.get('startDate'),
                'endDate': slot_data.get('endDate'),
                'remainingUses': 1,
                'offers': [{'@type': 'Offer', 'price': 0, 'priceCurrency': 'GBP'}],
                'beta:sportsActivityLocation': locations
            }
            
            # Process the missing slot for the available court
            self._process_missing_slot(missing_slot_data, court_info)
    
    def _process_missing_slot(self, slot_data: Dict, court_info: Dict, target_date: str = "", start_time: str = ""):
        """Process a missing slot for partially booked scenario"""
        locations = slot_data.get('beta:sportsActivityLocation', [])
        remaining_uses = slot_data.get('remainingUses', 0)
        
        # Clear any existing court entries and create only generic availability
        court_info.clear()
        
        # Create a generic "available courts" entry
        court_name = "Available Courts"
        court_id = "partial_booking"
        
        court_info[court_name] = {
            'id': court_id,
            'available': remaining_uses > 0,
            'remaining_uses': remaining_uses,
            'slots': [{
                'start': slot_data.get('startDate'),
                'end': slot_data.get('endDate'),
                'remaining': remaining_uses
            }]
        }
    
    def _process_multiple_court_slots(self, slot_group: List[Dict], court_info: Dict):
        """Process multiple slots at the same time (individual court slots)"""
        # Sort slots to ensure consistent court assignment
        slot_group.sort(key=lambda x: x.get('identifier', ''))
        
        for i, slot_data in enumerate(slot_group):
            remaining_uses = slot_data.get('remainingUses', 0)
            offers = slot_data.get('offers', [])
            price = offers[0].get('price', 0) if offers else 0
            locations = slot_data.get('beta:sportsActivityLocation', [])
            
            # Determine which court this slot belongs to based on availability
            # Available court (remaining: 1, price: 10.25) should be Court 2
            # Booked court (remaining: 0, price: 0) should be Court 1
            if remaining_uses > 0 and price > 0:
                # This is the available court - should be Court 2
                target_court_name = "Squash Court 2"
                target_court_id = "041ZSQU002"
            else:
                # This is the booked court - should be Court 1
                target_court_name = "Squash Court 1"
                target_court_id = "041ZSQU001"
            
            # Find the matching location
            court_name = None
            court_id = None
            for location in locations:
                location_name = location.get('name', '')
                location_id = location.get('identifier', '')
                if location_name == target_court_name:
                    court_name = location_name
                    court_id = location_id
                    break
            
            # Fallback to target if not found in locations
            if not court_name:
                court_name = target_court_name
                court_id = target_court_id
            
            if court_name not in court_info:
                court_info[court_name] = {
                    'id': court_id,
                    'available': False,
                    'remaining_uses': 0,
                    'slots': []
                }
            
            # Update availability for this specific court
            court_info[court_name]['remaining_uses'] = max(
                court_info[court_name]['remaining_uses'], remaining_uses
            )
            
            if remaining_uses > 0:
                court_info[court_name]['available'] = True
            
            court_info[court_name]['slots'].append({
                'start': slot_data.get('startDate'),
                'end': slot_data.get('endDate'),
                'remaining': remaining_uses
            })
    
    def check_squash_availability(self, target_date: str, start_time: str) -> Tuple[Dict, Dict, str, str, str, str]:
        """Check squash court availability for main slot and the period before it (40 minutes each)"""
        from datetime import datetime, timedelta
        
        # Calculate time ranges (always 40 minutes)
        main_start = start_time
        main_end = (datetime.strptime(start_time, "%H:%M") + timedelta(minutes=40)).strftime("%H:%M")
        
        before_start = (datetime.strptime(start_time, "%H:%M") - timedelta(minutes=40)).strftime("%H:%M")
        before_end = start_time
        
        all_slots = self.api.fetch_all_slots()
        
        # Check main slot availability
        main_slots = self.filter_squash_slots_by_time(all_slots, target_date, main_start, main_end)
        
        # Check before slot availability
        before_slots = self.filter_squash_slots_by_time(all_slots, target_date, before_start, before_end)
        
        main_court_info = self.get_squash_court_availability(main_slots)
        before_court_info = self.get_squash_court_availability(before_slots)
        
        return main_court_info, before_court_info, main_start, main_end, before_start, before_end
    
    def print_results(self, main_court_info: Dict, before_court_info: Dict, 
                     main_start: str, main_end: str, before_start: str, before_end: str):
        """Print squash availability results"""
        
        print(f"\n{'='*60}")
        print(f"SQUASH COURT AVAILABILITY REPORT")
        print(f"{'='*60}")
        
        # Main slot results
        print(f"\nMain Slot ({main_start}-{main_end}):")
        print("-" * 40)
        
        available_courts = []
        unavailable_courts = []
        partial_booking = False
        
        for court_name, court_data in main_court_info.items():
            if court_data['available']:
                available_courts.append(f"• {court_name} - {court_data['remaining_uses']} slots available")
            else:
                unavailable_courts.append(f"• {court_name} - Fully booked")
        
        # Check if this is a partial booking scenario
        if "partial_booking" in [court_data['id'] for court_data in main_court_info.values()]:
            partial_booking = True
        
        if available_courts:
            print(f"✅ AVAILABLE SQUASH COURTS ({len(available_courts)}):")
            for court in available_courts:
                print(f"  {court}")
            
            if partial_booking:
                print(f"\n📋 NOTE: Specific court availability not available in API data")
                print(f"🔗 Click here to see which court is available:")
                print(f"   https://placesleisure.gladstonego.cloud/book/calendar/041A000005")
        
        if unavailable_courts:
            print(f"❌ UNAVAILABLE SQUASH COURTS ({len(unavailable_courts)}):")
            for court in unavailable_courts:
                print(f"  {court}")
        
        # Before slot results
        print(f"\nBefore Slot ({before_start}-{before_end}):")
        print("-" * 40)
        
        available_courts_before = []
        unavailable_courts_before = []
        partial_booking_before = False
        
        for court_name, court_data in before_court_info.items():
            if court_data['available']:
                available_courts_before.append(f"• {court_name} - {court_data['remaining_uses']} slots available")
            else:
                unavailable_courts_before.append(f"• {court_name} - Fully booked")
        
        # Check if this is a partial booking scenario
        if "partial_booking" in [court_data['id'] for court_data in before_court_info.values()]:
            partial_booking_before = True
        
        if available_courts_before:
            print(f"✅ AVAILABLE SQUASH COURTS ({len(available_courts_before)}):")
            for court in available_courts_before:
                print(f"  {court}")
            
            if partial_booking_before:
                print(f"\n📋 NOTE: Specific court availability not available in API data")
                print(f"🔗 Click here to see which court is available:")
                print(f"   https://placesleisure.gladstonego.cloud/book/calendar/041A000005")
        
        if unavailable_courts_before:
            print(f"❌ UNAVAILABLE SQUASH COURTS ({len(unavailable_courts_before)}):")
            for court in unavailable_courts_before:
                print(f"  {court}")
        
        # Find courts available for both slots
        print(f"\nSQUASH COURTS AVAILABLE FOR BOTH SLOTS:")
        print("-" * 40)
        
        # Get available court names from both slots
        main_available = set()
        before_available = set()
        
        for court_name, court_data in main_court_info.items():
            if court_data['available']:
                main_available.add(court_name)
        
        for court_name, court_data in before_court_info.items():
            if court_data['available']:
                before_available.add(court_name)
        
        common_available = main_available.intersection(before_available)
        
        if common_available:
            print(f"  🎯 Courts available for both time slots:")
            for court in sorted(common_available):
                print(f"    {court}")
        else:
            print("  No squash courts available for both time slots.")
        
        print(f"\n{'='*60}")

def check_availability_programmatic(target_date: str, start_time: str) -> Dict:
    """
    Programmatic interface to check squash availability.
    Returns structured data instead of printing to stdout.
    """
    checker = SquashAvailabilityChecker()
    
    try:
        main_court_info, before_court_info, main_start, main_end, before_start, before_end = checker.check_squash_availability(target_date, start_time)
        
        # Count available slots for both time periods
        main_available = sum(1 for court_data in main_court_info.values() if court_data['available'])
        before_available = sum(1 for court_data in before_court_info.values() if court_data['available'])
        
        # Determine success and message
        if before_available > 0:
            if before_available == 1:
                message = "There is one slot free before your booking"
            else:
                message = f"There are {before_available} slots free before your booking"
            success = True
        else:
            message = "There is no slots free before your booking"
            success = False
        
        # Build booking URL with proper parameters
        from datetime import datetime, timezone
        
        # Parse the before slot start time to create proper datetime
        before_datetime = datetime.strptime(f"{target_date}T{before_start}:00", "%Y-%m-%dT%H:%M:%S")
        before_datetime_utc = before_datetime.replace(tzinfo=timezone.utc)
        
        # Calculate previous activity date (40 minutes before)
        previous_datetime = before_datetime_utc - timedelta(minutes=40)
        
        # Format dates for URL
        activity_date = before_datetime_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        previous_activity_date = previous_datetime.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        # Build the booking URL with parameters
        booking_url = f"https://placesleisure.gladstonego.cloud/book/calendar/041A000005?activityDate={activity_date}&previousActivityDate={previous_activity_date}"
        
        # Return structured result
        result = {
            "success": success,
            "message": message,
            "main_slot_available": main_available,
            "before_slot_available": before_available,
            "booking_url": booking_url,
            "main_court_info": main_court_info,
            "before_court_info": before_court_info,
            "time_slots": {
                "main": {"start": main_start, "end": main_end},
                "before": {"start": before_start, "end": before_end}
            }
        }
        
        return result
        
    except Exception as e:
        error_result = {
            "success": False,
            "message": f"Error checking availability: {str(e)}",
            "booking_url": "https://placesleisure.gladstonego.cloud/book/calendar/041A000005",
            "error": str(e)
        }
        return error_result

def main():
    parser = argparse.ArgumentParser(description='Check Places Leisure squash court availability')
    parser.add_argument('--date', help='Target date (YYYY-MM-DD). Defaults to today if not provided')
    parser.add_argument('--start-time', required=True, help='Start time (HH:MM) - checks 40-minute slot and 40 minutes before')
    
    args = parser.parse_args()
    
    # Default to today's date if not provided
    if args.date is None:
        from datetime import datetime
        args.date = datetime.now().strftime('%Y-%m-%d')
    
    # Use the programmatic interface and print the result
    result = check_availability_programmatic(args.date, args.start_time)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
