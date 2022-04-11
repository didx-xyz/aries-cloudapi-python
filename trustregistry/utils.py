from typing import List


def get_data_slice(data: List, start: int = None, end: int = None):
    data_entries_total = len(data)
    if not start:
        start = 0
    if not end:
        end = data_entries_total
    # Entries must be positive
    start = abs(start)
    end = abs(end)
    range_of_entries = abs(end - start)
    if start > end:
        # swap start and end
        start, end = end, start
    if data_entries_total < start or data_entries_total < end:
        # get the last n entries if range out of bounce
        end = data_entries_total - 1
        start = data_entries_total - range_of_entries
        if start < 0:
            start = 0
    return data[start:end]
