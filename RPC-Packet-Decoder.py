"""
MCU-MPU JSON Protocol Decoder
Input: Encoded JSON packet
Output: Decoded event type, Native content payload

(C) 2026 Alexandre Teixeira
"""

import json

class ADASPacketDecoder:
    def __init__(self):
        pass

    @staticmethod
    def decode_telemetry(json_line: str) -> tuple:
        """
        Parses a compact JSON string and returns a tuple: (type, content).
        Returns (None, None) if parsing fails or line is corrupted.
        """
        if not json_line:
            return None, None
            
        try:
            # Strip whitespace and line breaks
            clean_line = json_line.strip()
            if not clean_line:
                return None, None

            data = json.loads(clean_line)
            
            msg_type = data.get("type")
            content = data.get("content")
            
            if msg_type is None:
                return None, None

            return str(msg_type).upper(), content

        except (json.JSONDecodeError, AttributeError):
            # Gracefully handle truncated or corrupted serial frames
            return None, None


# Quick Local Test
if __name__ == "__main__":
    decoder = ADASPacketDecoder()

    # Sample incoming serial lines
    test_lines = [
        '{"type":"INIT", "content": ""}\n',
        '{"type":"INIT_ACK", "content": ""}\n',
        '{"type":"LIM", "content": 120}\n',
        '{"type":"SPD", "content": 118.4}\n',
        '{"type":"IMU", "content": {"ax":0.02,"ay":-0.45}}\n', # Nested object test
        '{"type":"TIP", "content": "HARSH BRAKE"}',
        'CORRUPTED_SERIAL_FRAME_1234\n',                      # Malformed test
        ''                                                    # Empty line test
    ]

    print("--- Decoding Test ---")
    for line in test_lines:
        msg_type, content = decoder.decode_telemetry(line)
        print(f"Input: {repr(line):<50} -> Type: {str(msg_type):<6} | Content: {content}")