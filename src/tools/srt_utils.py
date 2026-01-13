import re
from datetime import timedelta
from typing import List, Dict

class SRTSubtitle:
    def __init__(self, index: int, start: str, end: str, text: str):
        self.index = index
        self.start = start
        self.end = end
        self.text = text.strip()

def parse_srt(content: str) -> List[SRTSubtitle]:
    """Parse SRT content into subtitle objects"""
    subtitles = []
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            index = int(lines[0])
            timing = lines[1]
            text = '\n'.join(lines[2:])
            
            # Parse timing
            start_time, end_time = timing.split(' --> ')
            subtitles.append(SRTSubtitle(index, start_time, end_time, text))
    
    return subtitles

def generate_srt(subtitles: List[SRTSubtitle]) -> str:
    """Generate SRT format string from subtitle objects"""
    srt_content = []
    
    for subtitle in subtitles:
        srt_content.append(f"{subtitle.index}")
        srt_content.append(f"{subtitle.start} --> {subtitle.end}")
        srt_content.append(subtitle.text)
        srt_content.append("")
    
    return '\n'.join(srt_content)
