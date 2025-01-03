def calculate_pp(star_rating: float, testcase_count: int, time_taken: int,  wrong: int) -> int:
    """
    Calculate performance points (PP) based on star rating, testcase bonus, and penalty time.

    Args:
        star_rating (float): The star rating of the level (1 to 10).
        testcase_count (int): The number of test cases for the level.
        time_taken (int): The time taken to complete the level, in seconds.
        wrong (int): The number of wrong submissions.
    Returns:
        int: Calculated performance points (max 200, min 0).
    """
    max_pp = 200
    scaling_factor = 2
    pp = (star_rating / 10) ** scaling_factor * max_pp
    if wrong > 0:
        wrong = wrong * 1.5

    if testcase_count > 1:
        bonus = (testcase_count - 1) * 1
        pp += bonus

    pp = max(0, min(pp, max_pp)) # noqa

    perfect_runtime = 500 * testcase_count
    if time_taken is not None:
        if time_taken > perfect_runtime:
            penalty = ((time_taken - perfect_runtime) // 120) * 15
            pp -= penalty

    pp -= wrong
    if pp < 0:
        pp = 0
    return int(round(pp))

if __name__ == '__main__':
    print(calculate_pp(5, 4, 512, 5))
