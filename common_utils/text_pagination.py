"""
Functions related to breaking strings apart for word wrapping, and grouping them together again for pagination.
"""

from typing import List


def get_wrapped_lines(report: str, max_line_length: int) -> List[str]:
    """
    Given a string and a maximum line length, breaks the string apart
    into new lines.

    Attempts to respect any line breaks included in the source string.

    Args:
        report (str): The source string to break apart.
        max_line_length (int): The maximum number of characters in a line.

    Returns:
        list[str]: A set of lines that the source string has been broken into.

    >>> get_wrapped_lines('', 20)
    []
    >>> get_wrapped_lines('statute', 20)
    ['statute']
    >>> get_wrapped_lines('Willy Wonka', 8)
    ['Willy', 'Wonka']
    >>> get_wrapped_lines('   Willy   Wonka  ', 8)
    ['Willy', 'Wonka']
    >>> get_wrapped_lines('Willy\\nWonka', 80)
    ['Willy', 'Wonka']
    >>> get_wrapped_lines('Willy Wonka', 2)
    ['Willy', 'Wonka']
    >>> get_wrapped_lines('TAF KPAE 212320Z 2200/2224 11009G16KT P6SM -RA SCT020 BKN050\\nFM220100 13012KT 6SM -RA BR OVC020\\nFM220600 16014G21KT 6SM -RA BR OVC022\\nFM221200 15012G18KT P6SM VCSH OVC015\\nFM222100 15017G28KT 6SM -RA BR OVC025', 80)
    ['TAF KPAE 212320Z 2200/2224 11009G16KT P6SM -RA SCT020 BKN050', 'FM220100 13012KT 6SM -RA BR OVC020', 'FM220600 16014G21KT 6SM -RA BR OVC022', 'FM221200 15012G18KT P6SM VCSH OVC015', 'FM222100 15017G28KT 6SM -RA BR OVC025']
    >>> get_wrapped_lines('TAF KPAE 212320Z 2200/2224 11009G16KT P6SM -RA SCT020 BKN050\\nFM220100 13012KT 6SM -RA BR OVC020\\nFM220600 16014G21KT 6SM -RA BR OVC022\\nFM221200 15012G18KT P6SM VCSH OVC015\\nFM222100 15017G28KT 6SM -RA BR OVC025', 40)
    ['TAF KPAE 212320Z 2200/2224 11009G16KT', 'P6SM -RA SCT020 BKN050', 'FM220100 13012KT 6SM -RA BR OVC020', 'FM220600 16014G21KT 6SM -RA BR OVC022', 'FM221200 15012G18KT P6SM VCSH OVC015', 'FM222100 15017G28KT 6SM -RA BR OVC025']
    >>> get_wrapped_lines('TAF KPAE 212320Z 2200/2224 11009G16KT P6SM -RA SCT020 BKN050\\nFM220100 13012KT 6SM -RA BR OVC020\\nFM220600 16014G21KT 6SM -RA BR OVC022\\nFM221200 15012G18KT P6SM VCSH OVC015\\nFM222100 15017G28KT 6SM -RA BR OVC025', 20)
    ['TAF KPAE 212320Z', '2200/2224 11009G16KT', 'P6SM -RA SCT020', 'P6SM -RA SCT020', 'FM220100 BKN050', 'FM220100 13012KT 6SM', '-RA BR OVC020', 'FM220600 16014G21KT', '6SM -RA BR OVC022', 'FM221200 15012G18KT', 'P6SM VCSH OVC015', 'FM222100 15017G28KT', '6SM -RA BR OVC025']
    >>> get_wrapped_lines('TAF KPAE 220253Z 14007G15KT 9SM -RA SCT038 BKN045 OVC050 09/07 A3005 RMK AO2 RAE05B25 SLP179 P0000 60000 T00940072 55013', 20)
    ['TAF KPAE 220253Z', '14007G15KT 9SM -RA', 'SCT038 BKN045 OVC050', '09/07 A3005 RMK AO2', 'RAE05B25 SLP179 P0000', '60000 T00940072 55013']
    >>> get_wrapped_lines('010414 SFOS WA 010413 AMD\\nAIRMET SIERRA UPDT 1 FOR IFR AND MTN OBSCN VALID UNTIL 010900\\nAIRMET MTN OBSCN...WA OR CA\\nFROM 80WSW YXC TO 20WSW DNJ TO 20SE REO TO 50SSE LKV TO 60E RBL\\nTO RBL TO 30ENE ENI TO 30SW ENI TO 20SSW FOT TO ONP TO HQM TO\\nTOU TO HUH TO 80WSW YXC\\nMTNS OBSC BY CLDS/PCPN/BR. CONDS CONTG BYD 09Z THRU 15Z.\\nTHIS\\nIS\\nOVERFLOW', 39)
    ['010414 SFOS WA 010413 AMD', 'AIRMET SIERRA UPDT 1 FOR IFR AND MTN', 'OBSCN VALID UNTIL 010900', 'AIRMET MTN OBSCN...WA OR CA', 'FROM 80WSW YXC TO 20WSW DNJ TO 20SE REO', 'TO 50SSE LKV TO 60E RBL', 'TO RBL TO 30ENE ENI TO 30SW ENI TO 20SSW', 'FOT TO ONP TO HQM TO', 'TOU TO HUH TO 80WSW YXC', 'MTNS OBSC BY CLDS/PCPN/BR. CONDS CONTG', 'BYD 09Z THRU 15Z.', 'THIS', 'IS', 'OVERFLOW']
    """
    tokens = report.split(" ")

    lines: List[str] = []
    current_line = ""

    while tokens:
        next_token: str = tokens[0]
        token_length = len(next_token)

        return_lines = next_token.split("\n")

        if len(return_lines) > 1:
            new_addition = f" {return_lines[0]}".rstrip()

            if len(current_line) == 0:
                new_addition = new_addition.lstrip()

            if len(current_line) + len(new_addition) > max_line_length:
                lines.append(current_line)

                reversed_tokens = return_lines.copy()
                reversed_tokens.reverse()
                for split_token in reversed_tokens:
                    tokens.insert(0, split_token)
            else:
                current_line += new_addition
                lines.append(current_line)
                current_line = ""
                replacement_token = "\n".join(return_lines[1:])
                tokens = tokens[1:]
                tokens.insert(0, replacement_token)
                tokens.insert(
                    0, return_lines[0]
                )  # This is going to be removed anyway...
        elif len(current_line) + token_length > max_line_length:
            if len(current_line) > 0:
                lines.append(current_line.lstrip())
            current_line = next_token
        else:
            current_line += f" {next_token}"
            current_line = current_line.lstrip().rstrip()

        tokens = tokens[1:]

    if len(current_line) > 0:
        lines.append(current_line)

    return lines


def get_lines_grouped_by_page(
    all_lines: List[any], page_header: str, max_lines_per_page: int
) -> List[List[any]]:
    """
    Given a flat list of lines, group them into pages.
    Each page has a top level index that goes to a list of lines.

    Args:
        all_lines (List[any]): The flat list of lines we want to group into pages.
        page_header (str): Any page header to include at the top of each page. A value of None skips adding the header.
        max_lines_per_page (int): The maximum number of lines per page.

    Returns:
        List[List[any]]: The grouped set of pages.

    >>> get_lines_grouped_by_page([], None, 10)
    []
    >>> get_lines_grouped_by_page(['one', 'two'], None, 10)
    [['one', 'two']]
    >>> get_lines_grouped_by_page(['one', 'two'], 'zero', 10)
    [['zero', 'one', 'two']]
    >>> get_lines_grouped_by_page(['one', 'two'], 'zero', 2)
    [['zero', 'one'], ['zero', 'two']]
    >>> get_lines_grouped_by_page(['one', 'two'], None, 2)
    [['one', 'two']]
    >>> get_lines_grouped_by_page([1, 2, 3, 4, 5], 0, 4)
    [[0, 1, 2, 3], [0, 4, 5]]
    >>> get_lines_grouped_by_page([1, 2, 3], 0, 4)
    [[0, 1, 2, 3]]
    >>> get_lines_grouped_by_page([1, 2, 3, 4], 0, 4)
    [[0, 1, 2, 3], [0, 4]]
    >>> get_lines_grouped_by_page([1, 2, 3, 4], None, 4)
    [[1, 2, 3, 4]]
    """
    all_pages: List[List[any]] = []
    fresh_page: list[any] = [page_header] if page_header is not None else []

    while all_lines:
        page: List[any] = fresh_page.copy()
        take_count = max_lines_per_page - len(fresh_page)
        page += all_lines[:take_count]

        all_pages.append(page)

        all_lines = all_lines[take_count:]

    return all_pages


def get_consolidated_pages(
    pages_to_redistribute: List[List[any]], header: any, max_lines_per_page: int
) -> List[List[any]]:
    """
    Given a set of pages, consolidate pages into single pages when able.
    This will keep any set of lines together.

    Args:
        pages_to_redistribute (List[List[any]]): The pages to see if we can combine
        header (any): Any header to add to the top of a page. If 'None' then no header is added.
        max_lines_per_page (int): The maximum number of lines (header included) to consolidate into a single page.

    Returns:
        List[List[any]]: The new set of pages that has been consolidated

    >>> get_consolidated_pages([], None, 2)
    []
    >>> get_consolidated_pages([], 1, 2)
    [[1]]
    >>> get_consolidated_pages([['one', 'two']], None, 2)
    [['one', 'two']]
    >>> get_consolidated_pages([['one', 'two'], []], None, 2)
    [['one', 'two']]
    >>> get_consolidated_pages([['one', 'two'], ['three', 'four']], None, 4)
    [['one', 'two', 'three', 'four']]
    >>> get_consolidated_pages([['one', 'two'], ['three', 'four']], 'ZERO', 4)
    [['ZERO', 'one', 'two'], ['ZERO', 'three', 'four']]
    >>> get_consolidated_pages([[], ['one', 'two'], ['three', 'four'], []], 'ZERO', 4)
    [['ZERO', 'one', 'two'], ['ZERO', 'three', 'four']]
    >>> get_consolidated_pages([[1, 2, 3, 4], [5, 6], [7, 8], [9]], None, 4)
    [[1, 2, 3, 4], [5, 6, 7, 8], [9]]
    >>> get_consolidated_pages([[1, 2, 3, 4], [5, 6], [7, 8], [9]], '0', 4)
    [['0', 1, 2, 3], [4, '0', 5, 6], ['0', 7, 8, 9]]
    >>> get_consolidated_pages([['010414 SFOS WA 010413 AMD', 'AIRMET SIERRA UPDT 1 FOR IFR AND MTN', 'OBSCN VALID UNTIL 010900', 'AIRMET MTN OBSCN...WA OR CA', 'FROM 80WSW YXC TO 20WSW DNJ TO 20SE REO', 'TO 50SSE LKV TO 60E RBL', 'TO RBL TO 30ENE ENI TO 30SW ENI TO 20SSW', 'FOT TO ONP TO HQM TO', 'TOU TO HUH TO 80WSW YXC', 'MTNS OBSC BY CLDS/PCPN/BR. CONDS CONTG', 'BYD 09Z THRU 15Z.', 'THIS', 'IS', 'OVERFLOW']], ' STATION   REPORT', 11)
    [[' STATION   REPORT', '010414 SFOS WA 010413 AMD', 'AIRMET SIERRA UPDT 1 FOR IFR AND MTN', 'OBSCN VALID UNTIL 010900', 'AIRMET MTN OBSCN...WA OR CA', 'FROM 80WSW YXC TO 20WSW DNJ TO 20SE REO', 'TO 50SSE LKV TO 60E RBL', 'TO RBL TO 30ENE ENI TO 30SW ENI TO 20SSW', 'FOT TO ONP TO HQM TO', 'TOU TO HUH TO 80WSW YXC', 'MTNS OBSC BY CLDS/PCPN/BR. CONDS CONTG'], ['BYD 09Z THRU 15Z.', 'THIS', 'IS', 'OVERFLOW']]
    """
    consolidated_report_pages: List[List[any]] = []
    fresh_page: List[any] = [header] if header is not None else []
    new_page: List[any] = fresh_page.copy()

    if len(pages_to_redistribute) > 0:
        new_page += pages_to_redistribute[0]

        if len(new_page) >= max_lines_per_page:
            truncated_page = new_page[:max_lines_per_page]
            remaining_page = new_page[max_lines_per_page:]

            consolidated_report_pages.append(truncated_page)

            if len(pages_to_redistribute) > 1:
                remaining_page += fresh_page.copy()

            pages_to_redistribute[0] = remaining_page
            new_page = []
        else:
            new_page = fresh_page.copy()

    while pages_to_redistribute:
        potential_additional_lines = pages_to_redistribute[0]

        if len(new_page) > max_lines_per_page:
            truncated_page = new_page[:max_lines_per_page]
            remaining_page = new_page[max_lines_per_page:]

            consolidated_report_pages.append(truncated_page)

            pages_to_redistribute.insert(0, remaining_page)
            pages_to_redistribute.insert(0, truncated_page)
        elif (len(new_page) + len(potential_additional_lines)) > max_lines_per_page:
            consolidated_report_pages.append(new_page)

            new_page = fresh_page.copy()
            new_page += potential_additional_lines
        else:
            new_page += potential_additional_lines

        pages_to_redistribute = pages_to_redistribute[1:]

    if len(new_page) > 0:
        consolidated_report_pages.append(new_page)

    return consolidated_report_pages


if __name__ == "__main__":
    import doctest

    print("Starting pagination tests.")

    doctest.testmod()

    print("Tests pagination finished")
