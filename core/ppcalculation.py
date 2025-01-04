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
        wrong = wrong * 2.5

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

def ranking_calculation(status: str, pp: int = 0, max_pp: int = 0, star_rating: int = 0, compile_time: int = 0) -> str:
    """
    Calculate ranking based on performance points, maximum performance points, and other factors.

    Args:
        status (str): The status of the submission (ACCEPTED, WA, TLE, RE, CE).
        pp (int): The performance points of the user.
        max_pp (int): The maximum performance points possible for the level.
        star_rating (int): The difficulty rating of the level (1-10).
        compile_time (int): The time taken to compile the code, in milliseconds.

    Returns:
        str: Calculated ranking (S, A, B, C, D, F).
    """

    if status != "ACCEPTED":
        return "F"


    if max_pp <= 0:
        raise ValueError("max_pp must be greater than 0.")

    performance = pp / max_pp

    if performance == 1:
        rank = "SS"
    elif performance > 0.9:
        rank = "S"
    elif 0.8 <= performance < 0.9:
        rank = "A"
    elif 0.7 <= performance < 0.8:
        rank = "B"
    elif 0.6 <= performance < 0.7:
        rank = "C"
    elif 0.5 <= performance < 0.6:
        rank = "D"
    else:
        rank = "D"

    penalty_steps = compile_time // 5000
    for _ in range(penalty_steps):
        if rank == "D":
            break
        rank = chr(min(ord(rank) + 1, ord("D")))
    return rank

# DEBUG
if __name__ == '__main__':
    status = "ACCEPTED"
    star_rating = 8
    testcase_count = 4
    time_taken = 512
    wrong = 1
    pp = calculate_pp(star_rating, testcase_count, time_taken, wrong)
    maxpp = calculate_pp(star_rating, testcase_count, 0, 0)
    rank = ranking_calculation(status, pp, maxpp, star_rating, time_taken)
    print(f"PP: {pp} / {maxpp} | Rating: {star_rating} | Time: {time_taken} | Wrong: {wrong} | Rank: {rank} | SUBMISSION: {'Ranked' if status == 'ACCEPTED' else 'Not Ranked'}")

