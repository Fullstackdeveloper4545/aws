#!/usr/bin/env python3
"""
Train Data Parser for Lambda Handler
Parses asterisk-delimited train data files and converts to JSON format
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger()

def parse_filename(filename: str) -> Dict[str, str]:
    """
    Parse filename to extract siteID and train sequence number
    Format: YYYYMMDDHHmm-FileNo-SiteID_TrainSequenceNo.csv
    """
    # Remove file extension (everything after the last dot)
    name_without_ext = filename
    if '.' in filename:
        name_without_ext = filename.rsplit('.', 1)[0]
    
    # Split by underscore to get SiteID_TrainSequenceNo
    parts = name_without_ext.split('_')
    if len(parts) >= 2:
        # Extract siteID from the part before the last underscore
        site_id = parts[-2]  # Second to last part
        train_sequence = parts[-1]  # Last part
        
        # Clean up siteID if it contains the full path
        if '/' in site_id:
            site_id = site_id.split('/')[-1]
        
        # Validate that train_sequence is numeric
        if not train_sequence.isdigit():
            raise ValueError(f"Invalid filename format: train sequence number '{train_sequence}' is not numeric in filename '{filename}'")
        
        # Validate that site_id is not empty
        if not site_id or site_id.strip() == "":
            raise ValueError(f"Invalid filename format: site ID is empty in filename '{filename}'")
            
    else:
        raise ValueError(f"Invalid filename format: expected 'SiteID_TrainSequenceNo' pattern in filename '{filename}'")
    
    return {
        "siteID": site_id,
        "train_sequence_number": train_sequence
    }


def parse_aem_line(fields: List[str]) -> Dict[str, Any]:
    """
    Parse AEM (train header) line according to AEM structure
    AEM*IHTRR*IHT0001*210915*0646*0700*060*Y*411*0022*G*G*N*0*E*004*000*003*C*N*F*N*01666*H*01*01*025*025*0106
    """
    if len(fields) < 29:
        raise ValueError(f"Invalid AEM line: expected 29 fields, got {len(fields)}")
    
    # Parse date and time
    date_str = fields[3]  # AEM03: Event Start Date (YYMMDD)
    start_time = fields[4]  # AEM04: Event Start Time (HHMM)
    stop_time = fields[5]  # AEM05: Event Stop Time (HHMM)
    
    # Convert date format from YYMMDD to YYYY-MM-DD
    year = "20" + date_str[:2]
    month = date_str[2:4]
    day = date_str[4:6]
    formatted_date = f"{year}-{month}-{day}"
    
    # Convert time format from HHMM to HH:MM
    start_time_formatted = f"{start_time[:2]}:{start_time[2:]}"
    stop_time_formatted = f"{stop_time[:2]}:{stop_time[2:]}"
    
    # Create timestamp
    timestamp = f"{formatted_date} {start_time_formatted}"
    
    return {
        "segment_id": fields[0],                    # AEM00: Segment ID
        "aar_billing_code": fields[1],              # AEM01: AAR Billing Code
        "site_id": fields[2],                       # AEM02: Site ID
        "event_start_date": formatted_date,          # AEM03: Event Start Date
        "event_start_time": start_time_formatted,    # AEM04: Event Start Time
        "event_stop_time": stop_time_formatted,      # AEM05: Event Stop Time
        "timezone": float(fields[6]) / 10,          # AEM06: Time Zone (convert from 060 to 6.0)
        "daylight_saving": fields[7],               # AEM07: Daylight Savings Time Indicator
        "data_format_version": int(fields[8]),      # AEM08: Data Format Version Number
        "train_sequence_number": fields[9],         # AEM09: Train Sequence Number
        "locomotive_conversion_status": fields[10], # AEM10: Locomotive Conversion Status
        "railcar_conversion_status": fields[11],    # AEM11: Railcar Conversion Status
        "travel_direction": fields[12],             # AEM12: Direction of Travel
        "switch_direction": int(fields[13]) if fields[13].isdigit() else 0,  # AEM13: Switch/Direction Indicator
        "units_measure": fields[14],                # AEM14: Units of Measure
        "max_speed": fields[15],                    # AEM15: Maximum Speed
        "min_speed": fields[16],                    # AEM16: Minimum Speed
        "avg_speed": fields[17],                    # AEM17: Average Speed
        "movement_status": fields[18],              # AEM18: Movement Status
        "termination_state": fields[19],            # AEM19: Termination Status
        "transmission_type": fields[20],            # AEM20: Transmission Type
        "adjacent_track_occupied": fields[21],      # AEM21: Adjacent Track Occupied
        "train_length": int(fields[22]),           # AEM22: Train Length
        "equipment_status_code": fields[23],        # AEM23: Equipment Status Code
        "locomotive_count": int(fields[24]),       # AEM24: Locomotive Count
        "locomotives_tagged": int(fields[25]),     # AEM25: Locomotives Tagged
        "railcar_count": int(fields[26]),          # AEM26: Railcar Count
        "railcar_tagged": int(fields[27]),         # AEM27: Railcars Tagged
        "total_axle_count": int(fields[28])        # AEM29: Total Axle Count
    }, timestamp


def parse_rre_line(fields: List[str]) -> Dict[str, Any]:
    """
    Parse RRE (railcar) line
    RRE*001*D*UP  *0000003237*A* *S*G*A*99*99*002*05*01
    """
    if len(fields) < 15:
        raise ValueError(f"Invalid RRE line: expected 15 fields, got {len(fields)}")
    
    # Handle reserved field (can be empty or space)
    reserved = fields[6] if fields[6] and fields[6] != " " else None
    
    return {
        "segment_id": fields[0],                    # RRE00: Segment ID
        "sequence_number": int(fields[1]),          # RRE01: Sequence Number
        "equipment_group_code": fields[2],          # RRE02: Equipment Group Code
        "owner_code": fields[3].strip(),            # RRE03: Owner Code (remove trailing spaces)
        "owner_equipment_number": fields[4],        # RRE04: Owner Equipment Number
        "orientation": fields[5],                   # RRE05: Orientation
        "reserved": reserved,                       # RRE06: Reserved
        "axle_conversion_code": fields[7],         # RRE07: Axle Conversion Code
        "tag_status": fields[8],                   # RRE08: Tag Status
        "tag_detail_status": fields[9],             # RRE09: Tag Detail Status
        "hand_shakes_antenna0": int(fields[10]),   # RRE10: Hand Shakes Antenna 0
        "hand_shakes_antenna1": int(fields[11]),   # RRE11: Hand Shakes Antenna 1
        "speed_of_vehicle": int(fields[12]),       # RRE12: Speed of Vehicle
        "axle_count": int(fields[13]),             # RRE13: Axle Count
        "platform_count": int(fields[14])          # RRE14: Platform Count
    }


def parse_eot_line(fields: List[str]) -> Dict[str, Any]:
    """
    Parse EOT (end of train) line
    EOT*026*E*UPRQ*0000067046*99*00*K
    """
    if len(fields) < 8:
        raise ValueError(f"Invalid EOT line: expected 8 fields, got {len(fields)}")
    
    return {
        "segment_id": fields[0],                    # EOT00: Segment ID
        "sequence_number": int(fields[1]),          # EOT01: Sequence Number
        "equipment_group_code": fields[2],          # EOT02: Equipment Group Code
        "owner_code": fields[3],                    # EOT03: Owner Code
        "owner_equipment_number": fields[4],        # EOT04: Owner Equipment Number
        "hand_shakes_antenna0": int(fields[5]),    # EOT05: Hand Shakes Antenna 0
        "hand_shakes_antenna1": int(fields[6]),    # EOT06: Hand Shakes Antenna 1
        "tag_detail_status": fields[7]              # EOT07: Tag Detail Status
    }


def parse_eoc_line(fields: List[str]) -> Dict[str, Any]:
    """
    Parse EOC (end of content) line
    EOC*0000001521
    """
    if len(fields) < 2:
        raise ValueError(f"Invalid EOC line: expected 2 fields, got {len(fields)}")
    
    return {
        "segment_id": fields[0],                    # EOC00: Segment ID
        "total_byte_count": int(fields[1])         # EOC01: Total Byte Count
    }


def parse_train_data_to_json(file_content: str, filename: str) -> Optional[Dict[str, Any]]:
    """
    Parse train data file content and convert to JSON format
    Returns a single JSON object representing the entire train data file
    """
    try:
        # Parse filename to get siteID and train sequence
        file_info = parse_filename(filename)
        
        # Initialize result structure
        result = {
            "siteID": file_info["siteID"],
            "timestamp": "",
            "train_sequence_number": file_info["train_sequence_number"],
            "train": {},
            "cars": [],
            "EOT": {},
            "EOC": {}
        }
        
        # Parse each line in the file
        lines = file_content.strip().split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Split by asterisk 
            delimiter = line[3]
            fields = line.split(delimiter)
            
            try:
                segment_type = fields[0]
                
                if segment_type == "AEM":
                    train_data, timestamp = parse_aem_line(fields)
                    result["train"] = train_data
                    result["timestamp"] = timestamp
                    
                elif segment_type == "RRE":
                    car_data = parse_rre_line(fields)
                    result["cars"].append(car_data)
                    
                elif segment_type == "EOT":
                    eot_data = parse_eot_line(fields)
                    result["EOT"] = eot_data
                    
                elif segment_type == "EOC":
                    eoc_data = parse_eoc_line(fields)
                    result["EOC"] = eoc_data
                    
                else:
                    logger.warning(f"Unknown segment type '{segment_type}' on line {line_num}")
                    
            except Exception as e:
                logger.error(f"Error parsing line {line_num}: {e}")
                logger.error(f"Line content: {line}")
                continue
        
        logger.info(f"Successfully parsed train data file {filename}")
        return result
        
    except Exception as e:
        logger.error(f"Error parsing train data file {filename}: {str(e)}")
        return None