from json import load
import os
from random import choice
from re import compile, UNICODE
from logging import getLogger

logger = getLogger(__name__)

class ProblemHandler:
    def __init__(self):
        self.easy = []
        self.medium = []
        self.hard = []
        self.load_problems()

    @staticmethod
    def __replace_unicode_whitespace__(text):
        whitespace_pattern = compile(r'[^\S\r\n]', UNICODE)
        return whitespace_pattern.sub(" ", text)

    def __load__(self, problem, difficultly: str):
        match difficultly:
            case "Easy":
                self.easy.append(problem)
            case "Medium":
                self.medium.append(problem)
            case "Hard":
                self.hard.append(problem)
            case _:
                pass

    def load_problems(self):
        count = 0
        for dir in os.listdir("./client/problems/"):
            if dir == "Easy":
                for problem_name in os.listdir("./client/problems/" + dir):
                    if len(os.listdir("./client/problems/" + dir + "/" + problem_name)) == 0:
                        continue
                    self.__load__("./client/problems/" + dir + "/" + problem_name, "Easy")
                    count += 1
            elif dir == "Medium":
                for problem_name in os.listdir("./client/problems/" + dir):
                    if len(os.listdir("./client/problems/" + dir + "/" + problem_name)) == 0:
                        continue
                    self.__load__("./client/problems/" + dir + "/" + problem_name, "Medium")
                    count += 1
            if dir == "Hard":
                for problem_name in os.listdir("./client/problems/" + dir):
                    if len(os.listdir("./client/problems/" + dir + "/" + problem_name)) == 0:
                        continue
                    self.__load__("./client/problems/" + dir + "/" + problem_name, "Hard")
                    count += 1

        logger.info(f"Đã tải {count} vấn đề")

    @staticmethod
    def get_problem_config(path):
        with open(f"{path}/config.json", "r") as f:
            config = load(f)
        return config

    def get_problem_description(self, path):
        with open(f"{path}/problem.txt", "r") as f:
            return self.__replace_unicode_whitespace__(f.read())

    def get_random_problem(self):
        _random = [choice(self.easy), choice(self.medium), choice(self.hard)]
        return choice(_random)

    def get_problem_by_difficulty(self, difficulty: str):
        match difficulty.lower():
            case "easy":
                return choice(self.easy)
            case "medium":
                return choice(self.medium)
            case "hard":
                return choice(self.hard)
            case _:
                return None


# debug
if __name__ == "__main__":
    problems = ProblemHandler()
    p = problems.get_random_problem()
    print(problems.get_problem_config(p))
    print("-"*40)
    print(problems.get_problem_description(p))
            
