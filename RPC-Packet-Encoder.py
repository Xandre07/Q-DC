"""
MCU-MPU JSON Protocol Encoder
Input: Event type, Native content payload
Output: Encoded JSON packet

(C) 2026 Alexandre Teixeira
"""
import json

class ADASPacketBuilder:
    def __init__(self):
        pass

    @staticmethod
    def encode_telemetry(msg_type: str, content) -> str:
        """
        Packs ADAS events into a compact JSON string terminated with a newline.
        Example outputs: 
          {"type":"LIM","content":120}\n
        """
        payload = {
            "type": str(msg_type).upper(),
            "content": content
        }
        
        return json.dumps(payload, separators=(',', ':')) + "\n"


if __name__ == "__main__":
    builder = ADASPacketBuilder()
    
    # Test different payload content types
    print(repr(builder.encode_telemetry("LIM", 120)))         # Integer
    print(repr(builder.encode_telemetry("SPD", 118.4)))       # Float
    print(repr(builder.encode_telemetry("TIP", "HARSH BRAKE")))# String
    print(repr(builder.encode_telemetry("LDW", 1)))           # Int flag