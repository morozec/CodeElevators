from core.base_strategy import BaseStrategy
import math
import json
from typing import List

FIRST_FLOOR = 1
LAST_FLOOR = 9
PASS_CREATION_TIME = 2000
current_tick = 1

FLOOR_TIME = 50
CRITICAL_PASS_COUNT = 10
CRITICAL_PASS_COEFF = 1.1
CLOSE_OPEN_TIME = 100
DELAY_FLOOR_TIME = 40
FLOOR_WALKING_TIME = 500
WAIT_ELEVATOR_TIME = 500
PASSENGER_SPEED = 2
POINTS_PER_PASS = 10
ELEVATOR_WAITING_TIME = 1

START_X = 20

all_passengers = {}
walking_passengers = {}
is_self_passengers = {}

elevator_states = {
    1: 3,
    2: 3,
    3: 3,
    4: 3,
    5: 3,
    6: 3,
    7: 3,
    8: 3,
}

waiting_elevators = {
    1: False,
    2: False,
    3: False,
    4: False,
    5: False,
    6: False,
    7: False,
    8: False,
}

closing_elevators_time = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
    7: 0,
    8: 0,
}

MAX_STEPS = 5

FLOOR_HEIGHT = 1

STAIRWAY_SPEED_UP = 1 / 200
STAIRWAY_SPEED_DOWN = 1 / 100

GAME_TIME = 7200
FIRST_PLAYER = "FIRST_PLAYER"
SECOND_PLAYER = "SECOND_PLAYER"
POINT_PER_WALKING_PASS = 40
path_containers_to_save = []
passengers_targets = {}
passengers_steps = {}
EPS_TIME = 10


def get_elevator_x(elevator):
    start_x = 60
    step_x = 80
    x = {
        1: -start_x - step_x * 0,
        3: -start_x - step_x * 1,
        5: -start_x - step_x * 2,
        7: -start_x - step_x * 3,
        2: start_x + step_x * 0,
        4: start_x + step_x * 1,
        6: start_x + step_x * 2,
        8: start_x + step_x * 3
    }
    return x[elevator.id]


def get_pass_elevator_time(passenger_x, elevator):
    global PASSENGER_SPEED
    length = abs(passenger_x - get_elevator_x(elevator))
    return math.ceil(length / PASSENGER_SPEED)


def get_elevator_by_id(my_elevators, enemy_elevators, key):
    my_elevator = [e for e in my_elevators if e.id == key]
    if len(my_elevator) > 0:
        return my_elevators[0]
    enemy_elevator = [e for e in enemy_elevators if e.id == key]
    if len(enemy_elevator) > 0:
        return enemy_elevator[0]
    raise NameError("Unknown elevator id")


# Считает время, за которое лифт доедет до этажа и откроет двери
def get_time_to_floor_for_real_elevator(elevator):
    global FLOOR_TIME
    global CRITICAL_PASS_COEFF
    global CRITICAL_PASS_COUNT
    global ELEVATOR_WAITING_TIME
    global closing_elevators_time

    target_floor = get_elevator_target_floor(elevator)

    diff = abs(elevator.y - target_floor)
    time = diff * FLOOR_TIME
    if elevator.y < target_floor:
        not_exiting_passengers = [p for p in elevator.passengers if p.dest_floor != elevator.floor]
        for p in not_exiting_passengers:
            time *= p.weight
        if len(not_exiting_passengers) > CRITICAL_PASS_COUNT:
            time *= CRITICAL_PASS_COEFF

    # DONE: время закрываения лифта
    add_delays = {
        0: CLOSE_OPEN_TIME,
        1: CLOSE_OPEN_TIME,
        2: CLOSE_OPEN_TIME - elevator.time_on_floor,
        # + 1, т.к. команда подействует со следующего тика
        3: 0 if target_floor == elevator.floor else CLOSE_OPEN_TIME + ELEVATOR_WAITING_TIME + CLOSE_OPEN_TIME + 1,
        4: closing_elevators_time[elevator.id] + ELEVATOR_WAITING_TIME + CLOSE_OPEN_TIME
    }
    time += add_delays[elevator.state]
    return math.ceil(time)


# Метод рассчитывает время перемещения с этажа source_floor на этаж dest_floor (не должны совпадать)
# с учетом закрытия, откытия дверей
def get_time_to_floor_for_virtual_elevator(source_floor, dest_floor, passengers):
    global FLOOR_TIME
    global CRITICAL_PASS_COEFF
    global CRITICAL_PASS_COUNT
    global CLOSE_OPEN_TIME
    global DELAY_FLOOR_TIME

    if source_floor == dest_floor:
        raise NameError("The same source and dest floors in get_time_to_floor_for_virtual_elevator")

    diff = abs(source_floor - dest_floor)
    time = diff * FLOOR_TIME
    if source_floor < dest_floor:
        not_exiting_passengers = [p for p in passengers if p.dest_floor != source_floor]
        for p in not_exiting_passengers:
            time *= p.weight
        if len(not_exiting_passengers) > CRITICAL_PASS_COUNT:
            time *= CRITICAL_PASS_COEFF

    # надо закрыть двери и открыть на нужном этаже (+1, т.к. команда будет действовать на след. ход)
    time += CLOSE_OPEN_TIME + ELEVATOR_WAITING_TIME + CLOSE_OPEN_TIME + 1
    return math.ceil(time)


def get_time_to_floor_for_stairway(passenger):
    global STAIRWAY_SPEED_DOWN
    global STAIRWAY_SPEED_UP
    dist = abs(passenger.y - passenger.dest_floor)
    speed = STAIRWAY_SPEED_UP if passenger.y < passenger.dest_floor else STAIRWAY_SPEED_DOWN
    # TODO: почему + 1 - непонятно
    return dist / speed + 1


def call_start_ticks_passengers(elevator, ok_my_passengers, ok_enemy_passengers):
    is_1_lift = \
        elevator.type == "FIRST_PLAYER" and elevator.id == 1 or elevator.type == "SECOND_PLAYER" and elevator.id == 2
    is_2_lift = \
        elevator.type == "FIRST_PLAYER" and elevator.id == 3 or elevator.type == "SECOND_PLAYER" and elevator.id == 4
    is_3_lift = \
        elevator.type == "FIRST_PLAYER" and elevator.id == 5 or elevator.type == "SECOND_PLAYER" and elevator.id == 6

    if is_1_lift:
        for p in [p for p in ok_my_passengers if p.floor == elevator.floor and p.dest_floor >= 8]:
            p.set_elevator(elevator)
        for p in [p for p in ok_enemy_passengers if p.floor == elevator.floor and p.dest_floor >= 8]:
            p.set_elevator(elevator)
    elif is_2_lift:
        for p in [p for p in ok_my_passengers if p.floor == elevator.floor and 6 <= p.dest_floor <= 7]:
            p.set_elevator(elevator)
        for p in [p for p in ok_enemy_passengers if p.floor == elevator.floor and 6 <= p.dest_floor <= 7]:
            p.set_elevator(elevator)
    elif is_3_lift:
        for p in [p for p in ok_my_passengers if p.floor == elevator.floor and (p.dest_floor == 5 or p.dest_floor == 9)]:
            p.set_elevator(elevator)
        for p in [p for p in ok_enemy_passengers if
                  p.floor == elevator.floor and (p.dest_floor == 5 or p.dest_floor == 9)]:
            p.set_elevator(elevator)
    else:
        for p in [p for p in ok_my_passengers if p.floor == elevator.floor and (p.dest_floor == 4 or p.dest_floor == 8)]:
            p.set_elevator(elevator)
        for p in [p for p in ok_enemy_passengers if
                  p.floor == elevator.floor and (p.dest_floor == 4 or p.dest_floor == 8)]:
            p.set_elevator(elevator)


def call_passengers(elevator, ok_my_passengers, ok_enemy_passengers, enemy_elevators):
    global DELAY_FLOOR_TIME
    global CLOSE_OPEN_TIME

    this_floor_my_passengers = [p for p in ok_my_passengers if p.floor == elevator.floor]
    this_floor_enemy_passengers = [p for p in ok_enemy_passengers if p.floor == elevator.floor]

    empty_places = 20 - len([p for p in elevator.passengers if p.dest_floor != elevator.floor])

    if len(this_floor_my_passengers) + len(this_floor_enemy_passengers) <= empty_places:  # свободных мест достаточно
        for p in this_floor_my_passengers:
            p.set_elevator(elevator)
        for p in this_floor_enemy_passengers:
            p.set_elevator(elevator)
    else:
        elevator_x = get_elevator_x(elevator)
        enemy_elevator, enemy_elevator_time = get_enemy_elevator_to_floor(enemy_elevators, elevator.floor)

        this_floor_passengers = [p for p in this_floor_my_passengers]
        this_floor_passengers += [p for p in this_floor_enemy_passengers]

        if enemy_elevator is None:  # нет чужого лифта на этаже

            ordered_this_floor_passengers = sorted(
                this_floor_passengers, key=lambda p: get_pass_points(p, elevator), reverse=True)

            for i in range(0, empty_places):
                ordered_this_floor_passengers[i].set_elevator(elevator)

        else:  # есть чужой лифт на этаже
            # Зовем всех чужих
            enemy_elevator_x = get_elevator_x(enemy_elevator)

            my_call_win_passengers = []
            my_call_loss_passengers = []

            for p in this_floor_passengers:
                if is_my_call_win(p.x, elevator_x,
                                  0 if elevator.time_on_floor > CLOSE_OPEN_TIME + DELAY_FLOOR_TIME
                                  else CLOSE_OPEN_TIME + DELAY_FLOOR_TIME - elevator.time_on_floor,
                                  enemy_elevator_x, enemy_elevator_time):
                    my_call_win_passengers += [p]
                else:
                    my_call_loss_passengers += [p]

            ordered_my_call_win_passengers = sorted(
                my_call_win_passengers, key=lambda p: get_pass_points(p, elevator), reverse=True)
            ordered_my_call_loss_passengers = sorted(
                my_call_loss_passengers, key=lambda p: get_pass_points(p, elevator), reverse=True)

            for i in range(0, min(empty_places, len(ordered_my_call_win_passengers))):
                ordered_my_call_win_passengers[i].set_elevator(elevator)

            empty_places = empty_places - len(ordered_my_call_win_passengers)
            if empty_places > 0:
                for i in range(0, min(empty_places, len(ordered_my_call_loss_passengers))):
                    ordered_my_call_loss_passengers[i].set_elevator(elevator)


def get_one_pass_points(source_floor, dest_floor):
    global POINTS_PER_PASS
    return abs(source_floor - dest_floor) * POINTS_PER_PASS


def get_pass_points(passenger, elevator):
    global POINTS_PER_PASS

    # пассажир который едет туда же, куда имеющиеся пассажиры - очень выгоден
    if len([p for p in elevator.passengers if p.dest_floor == passenger.dest_floor]) > 0:
        points = 1000
    else:
        points = abs(passenger.from_floor - passenger.dest_floor) * POINTS_PER_PASS
        if passenger.type != elevator.type:
            points *= 2

    return points


class VirtualPassenger:
    def __init__(self, key: int, floor: int):
        global POINT_PER_WALKING_PASS
        global is_self_passengers
        global FIRST_FLOOR
        global LAST_FLOOR
        global POINTS_PER_PASS
        global passengers_targets
        global passengers_steps

        self.key = key
        self.floor = floor
        self.floor_probs = {}
        self.floor_points = {}

        is_self = is_self_passengers[key]

        floors = range(FIRST_FLOOR, LAST_FLOOR + 1)
        if len(passengers_targets[key]) - passengers_steps[key] >= 2:
            target_floor = passengers_targets[key][passengers_steps[key] + 1]
            for c_floor in floors:

                if c_floor == target_floor:
                    self.floor_probs[c_floor] = 1
                    diff = abs(c_floor - floor)
                    self.floor_points[c_floor] = diff * POINTS_PER_PASS
                    if not is_self:
                        self.floor_points[c_floor] *= 2
                else:
                    self.floor_probs[c_floor] = 0
                    self.floor_points[c_floor] = 0

        else:
            prob = 1 / (len(floors) - 1)
            for c_floor in floors:
                self.floor_probs[c_floor] = prob if c_floor != floor else 0

                diff = abs(c_floor - floor)
                self.floor_points[c_floor] = diff * POINTS_PER_PASS
                if not is_self:
                    self.floor_points[c_floor] *= 2


class StepContainer:
    def __init__(self, points: int, floor: int, time: float, leaving_passengers_count: int,
                 leaving_virtual_passengers_count: int, filling_waiting_count: int, filling_walking_count):
        global current_tick

        self.points = points
        self.floor = floor
        self.time = time
        self.leaving_passengers_count = leaving_passengers_count
        self.leaving_virtual_passengers_count = leaving_virtual_passengers_count
        self.filling_waiting_count = filling_waiting_count
        self.filling_walking_count = filling_walking_count
        self.full_time = time + current_tick


class PathContainer:
    def __init__(self, curr_tick, elevator_id, current_floor, step_containers_list):
        self.curr_tick = curr_tick
        self.elevator_id = elevator_id
        self.current_floor = current_floor
        self.step_containers_list = step_containers_list

    @staticmethod
    def get_full_time(step_containers):
        return step_containers[-1].time

    @staticmethod
    def get_full_points(step_containers):
        res = 0
        for item in step_containers:
            res += item.points
        return res

    def get_points_per_time(self, step_containers):
        return self.get_full_points(step_containers) / self.get_full_time(step_containers)

    def get_best_step_containers(self):
        return max(self.step_containers_list, key=lambda sc: self.get_points_per_time(sc))

    def to_json(self):
        data = json.dumps(self, default=lambda o: o.__dict__, sort_keys=False, indent=4)
        return data


class BestPathContainer:

    def __init__(self, curr_tick, elevator_id, current_floor, is_time_finished, best_step_containers):
        self.curr_tick = curr_tick
        self.elevator_id = elevator_id
        self.current_floor = current_floor
        self.is_time_finished = is_time_finished
        self.best_step_containers = best_step_containers

    def to_json(self):
        data = json.dumps(self, default=lambda o: o.__dict__, sort_keys=False, indent=4)
        return data


def get_pass_start_x(pass_id, self_type):
    global is_self_passengers
    global START_X

    is_self = is_self_passengers[pass_id]
    if is_self and self_type == FIRST_PLAYER:
        return -START_X
    if is_self and self_type == SECOND_PLAYER:
        return START_X
    if not is_self and self_type == FIRST_PLAYER:
        return START_X
    if not is_self and self_type == SECOND_PLAYER:
        return -START_X
    raise NameError("Unknown arguments combination")


def is_my_call_win(pass_x, my_elevator_x, my_elevator_time, enemy_elevator_x, enemy_elevator_time):
    if my_elevator_time < enemy_elevator_time:
        return True
    elif my_elevator_time > enemy_elevator_time:
        return False
    else:
        return abs(my_elevator_x - pass_x) <= abs(enemy_elevator_x - pass_x)


def get_enemy_elevator_to_floor(enemy_elevators, floor):
    min_time = 999999
    elevator = None
    for e in enemy_elevators:
        if e.next_floor == -1 and e.floor != floor or e.next_floor != -1 and e.next_floor != floor:
            continue
        time = get_time_to_floor_for_real_elevator(e)
        if time < min_time:
            min_time = time
            elevator = e
    return elevator, min_time


def get_walking_passenger_points(key, current_floor):
    # DONE: уточнить с учетом текущего этажа
    global POINT_PER_WALKING_PASS
    global is_self_passengers
    global FIRST_FLOOR
    global LAST_FLOOR
    global POINTS_PER_PASS

    sum_points = 0
    floors = range(FIRST_FLOOR, LAST_FLOOR + 1)
    prob = 1 / (len(floors) - 1)
    for floor in floors:
        if floor == current_floor:
            continue
        diff = abs(floor - current_floor)
        sum_points += diff * POINTS_PER_PASS * prob

    is_self = is_self_passengers[key]
    if not is_self:
        sum_points *= 2
    return sum_points


def get_exiting_virtual_passengers(virtual_passengers: List[VirtualPassenger], floor: int):
    prob = 0
    for p in virtual_passengers:
        prob += p.floor_probs[floor]
    round_prob = int(round(prob))
    ordered_virtual_passengers = sorted(virtual_passengers, key=lambda v_p: v_p.floor_probs[floor], reverse=True)
    return ordered_virtual_passengers[:round_prob]


def get_elevator_target_floor(elevator):
    return elevator.next_floor if elevator.next_floor != -1 else elevator.floor


def get_step_containers(current_passengers, current_floor, current_time,
                        current_my_waiting_passengers, current_enemy_waiting_passengers, elevator, step,
                        my_elevators, enemy_elevators, virtual_passengers, current_floor_step):
    global FIRST_FLOOR
    global LAST_FLOOR
    global WAIT_ELEVATOR_TIME
    global MAX_STEPS
    global is_self_passengers
    global GAME_TIME
    global current_tick
    global DELAY_FLOOR_TIME
    global START_X

    global all_passengers
    global walking_passengers
    global is_self_passengers

    step_containers = []
    is_my_elevator_coming = len(
        [e for e in my_elevators if e.id != elevator.id and get_elevator_target_floor(e) == current_floor]) > 0

    if current_floor_step < MAX_STEPS and len(current_passengers) < 20 and not is_my_elevator_coming:
        this_floor_walking_passengers = {}
        for key in [key for key in walking_passengers.keys() if all_passengers[key] == current_floor]:
            if walking_passengers[key] in this_floor_walking_passengers.keys():
                this_floor_walking_passengers[walking_passengers[key]] += [key]
            else:
                this_floor_walking_passengers[walking_passengers[key]] = [key]

        this_floor_walking_passengers_list = []
        for key, value in this_floor_walking_passengers.items():
            this_floor_walking_passengers_list += [[key, value]]

        ordered_this_floor_walking_passengers_list = sorted(this_floor_walking_passengers_list,
                                                            key=lambda x: x[0])

        if len(ordered_this_floor_walking_passengers_list) > current_floor_step:
            item = ordered_this_floor_walking_passengers_list[current_floor_step]

            appear_time = item[0]
            appearing_ids = item[1]

            # DONE: нормальный расчет времени получения очков вместо appear_time (или appear_time + pass_time)
            if appear_time > current_time and appear_time + current_tick < GAME_TIME:
                enemy_elevator, enemy_elevator_time = get_enemy_elevator_to_floor(enemy_elevators, current_floor)
                new_virtual_passengers = [p for p in virtual_passengers]
                max_pass_time = 0
                for key in appearing_ids:

                    start_x = get_pass_start_x(key, elevator.type)

                    is_self = is_self_passengers[key]
                    my_call_time = appear_time if is_self else max([appear_time, DELAY_FLOOR_TIME])

                    if enemy_elevator is not None:
                        enemy_call_time = enemy_elevator_time if not is_self else enemy_elevator_time + DELAY_FLOOR_TIME
                        enemy_call_time = max([enemy_call_time, appear_time])
                        is_my_pass = is_my_call_win(start_x, get_elevator_x(elevator), my_call_time,
                                                    get_elevator_x(enemy_elevator),
                                                    enemy_call_time)
                        if not is_my_pass:
                            continue

                    pass_time = get_pass_elevator_time(start_x, elevator)
                    if pass_time > max_pass_time:
                        max_pass_time = pass_time

                    if len(current_passengers) + len(new_virtual_passengers) < 20:
                        new_virtual_passengers += [VirtualPassenger(key, current_floor)]
                    else:
                        break

                leaving_time = appear_time + max_pass_time  # Ждем пассажира, потом валим

                filling_waiting_count = 0
                filling_walking_count = len(new_virtual_passengers) - len(virtual_passengers)
                step_container = StepContainer(0, current_floor,  leaving_time, 0, 0,
                                               filling_waiting_count,
                                               filling_walking_count)

                if step < MAX_STEPS:
                    step_containers_tmp = get_step_containers(current_passengers, current_floor, leaving_time,
                                                              current_my_waiting_passengers,
                                                              current_enemy_waiting_passengers,
                                                              elevator, step + 1, my_elevators,
                                                              enemy_elevators,
                                                              new_virtual_passengers, current_floor_step + 1)

                    if len(step_containers_tmp) == 0:
                        step_containers.append([step_container])
                    else:
                        for sc in step_containers_tmp:
                            step_containers.append([step_container] + sc)
                else:
                    step_containers.append([step_container])

    floors = range(FIRST_FLOOR, LAST_FLOOR + 1)
    for floor in floors:

        if floor == current_floor:
            continue

        time_to_floor = get_time_to_floor_for_virtual_elevator(current_floor, floor, current_passengers)
        full_time_to_floor = current_time + time_to_floor
        full_time_to_leave = full_time_to_floor + DELAY_FLOOR_TIME

        if current_tick + full_time_to_floor > GAME_TIME:  # поехав на этот этаж, не успеем до конца игры
            continue

        exiting_passengers = [p for p in current_passengers if p.dest_floor == floor]
        exiting_virtual_passengers = get_exiting_virtual_passengers(virtual_passengers, floor)

        points = 0
        for p in exiting_passengers:
            one_pass_points = get_one_pass_points(p.from_floor, floor)
            if p.type != elevator.type:
                one_pass_points *= 2
            points += one_pass_points

        for p in exiting_virtual_passengers:
            points += p.floor_points[floor]

        got_passengers = False

        new_passengers = [p for p in current_passengers if p not in exiting_passengers]
        new_virtual_passengers = [p for p in virtual_passengers if p not in exiting_virtual_passengers]

        is_my_elevator_coming = len(
            [e for e in my_elevators if e.id != elevator.id and get_elevator_target_floor(e) == floor]) > 0
        if not is_my_elevator_coming:

            enemy_elevator, enemy_elevator_time = get_enemy_elevator_to_floor(enemy_elevators, floor)

            new_my_waiting_passengers = []
            for p in current_my_waiting_passengers:
                if enemy_elevator is not None:
                    is_my_pass = is_my_call_win(p.x, get_elevator_x(elevator), full_time_to_floor,
                                                get_elevator_x(enemy_elevator),
                                                enemy_elevator_time + DELAY_FLOOR_TIME)
                    if not is_my_pass:
                        continue
                if p.floor == floor and p.time_to_away > full_time_to_floor + get_pass_elevator_time(
                        p.x, elevator) and len(new_passengers) + len(new_virtual_passengers) < 20:
                    new_passengers += [p]
                    got_passengers = True
                else:
                    new_my_waiting_passengers += [p]

            new_enemy_waiting_passengers = []
            for p in current_enemy_waiting_passengers:
                if enemy_elevator is not None:
                    is_my_pass = is_my_call_win(p.x, get_elevator_x(elevator), full_time_to_leave,
                                                get_elevator_x(enemy_elevator),
                                                enemy_elevator_time)
                    if not is_my_pass:
                        continue

                if p.floor == floor and p.time_to_away > full_time_to_leave + get_pass_elevator_time(
                        p.x, elevator) and len(new_passengers) + len(new_virtual_passengers) < 20:
                    new_passengers += [p]
                    got_passengers = True
                else:
                    new_enemy_waiting_passengers += [p]

            # DONE: start pass x
            # DONE: подумать об увеличении числа new_passengers, чтобы на следующем шаге не набрать лишних
            new_passengers_length = len(new_passengers)
            for key in walking_passengers.keys():
                if all_passengers[key] != floor:
                    continue
                start_x = get_pass_start_x(key, elevator.type)
                is_self = is_self_passengers[key]
                my_call_time = full_time_to_floor if is_self else full_time_to_leave

                if enemy_elevator is not None:
                    enemy_call_time = enemy_elevator_time if not is_self else enemy_elevator_time + DELAY_FLOOR_TIME
                    is_my_pass = is_my_call_win(start_x, get_elevator_x(elevator),
                                                my_call_time,
                                                get_elevator_x(enemy_elevator),
                                                enemy_call_time)
                    if not is_my_pass:
                        continue

                # появятся раньше, чем элеватор будет готов их принять и исчезнут позже, чем они до него доберутся
                # DONE: учесть, что своих можно звать на 40 тиков раньше
                # если пассажир появится позже, чем walking_passengers[key] < full_time_to_leave, то он будет учтен выше
                appears_before_leave = walking_passengers[key] < full_time_to_leave
                disappears_after_filling = \
                    walking_passengers[key] + WAIT_ELEVATOR_TIME > my_call_time + get_pass_elevator_time(start_x, elevator)
                has_empty_space = new_passengers_length + len(new_virtual_passengers) < 20
                if appears_before_leave and disappears_after_filling and has_empty_space:
                    got_passengers = True
                    new_virtual_passengers += [VirtualPassenger(key, floor)]
        else:
            new_my_waiting_passengers = current_my_waiting_passengers
            new_enemy_waiting_passengers = current_enemy_waiting_passengers

        if len(exiting_passengers) != 0 or got_passengers:
            filling_waiting_count = \
                len(new_passengers) - (len(current_passengers) - len(exiting_passengers))
            filling_walking_count = len(new_virtual_passengers) - \
                                    (len(virtual_passengers) - len(exiting_virtual_passengers))
            step_container = StepContainer(points, floor, full_time_to_leave, len(exiting_passengers),
                                           len(exiting_virtual_passengers),
                                           filling_waiting_count,
                                           filling_walking_count)

            if step < MAX_STEPS:
                step_containers_tmp = get_step_containers(new_passengers, floor, full_time_to_leave,
                                                          new_my_waiting_passengers, new_enemy_waiting_passengers,
                                                          elevator, step + 1, my_elevators, enemy_elevators,
                                                          new_virtual_passengers, 0)

                if len(step_containers_tmp) == 0:
                    step_containers.append([step_container])
                else:
                    for sc in step_containers_tmp:
                        step_containers.append([step_container] + sc)
            else:
                step_containers.append([step_container])

    return step_containers


def get_passenger_elevator(passenger, my_elevators, enemy_elevators):
    my_elevators_pass = [e for e in my_elevators if e.id == passenger.elevator]
    if len(my_elevators_pass) > 0:
        return my_elevators_pass[0]
    enemy_elevators_pass = [e for e in enemy_elevators if e.id == passenger.elevator]
    if len(enemy_elevators_pass) > 0:
        return enemy_elevators_pass[0]
    return None


def get_optimal_elevator_path(elevator, my_passengers, enemy_passengers, my_elevators, enemy_elevators):
    global path_containers_to_save
    global current_tick
    global GAME_TIME
    # DONE: учитывать окончание игры
    # DONE: проверять, что на целевой этаж едет другой лифт
    # TODO: брать не всех пассажиров с этажа, а определенных
    # DONE: приоритет на чужих пассажиров
    # DONE: удваивать очки за чужих пассажиров, которые не в моем лифте
    # DONE: учитывать чужие лифты, которые едут на этаж
    # DONE: проверить вариант с удельными очками на тики
    # DONE: если осталось мало веремени, ехать даже на этаж, куда едет кто-то еще
    # TODO: не убегать, если пассажир идет к чужому лифту и не влезет туда
    # TODO: взятие пассажиров в начале игры
    # DONE: ждать, пока пассажир появится, не убегать сразу
    # TODO: в начале брать всех пассажиров, если больше не появятся. можно узжать раньше
    # DONE: не успеваем закочнить

    my_waiting_passengers = [p for p in my_passengers if (p.state == 1 or p.state == 3)]
    enemy_waiting_passengers = [p for p in enemy_passengers if (p.state == 1 or p.state == 3)]

    # TODO: нормальный критерий вместо "True if current_tick < GAME_TIME - 1500 else False"
    step_containers = get_step_containers([p for p in elevator.passengers if p.dest_floor != elevator.floor],
                                          elevator.floor, 0,
                                          my_waiting_passengers, enemy_waiting_passengers, elevator, 0,
                                          my_elevators,
                                          enemy_elevators, [], 0)

    if len(step_containers) == 0:
        return -1, 0

    path_container = PathContainer(current_tick, elevator.id, elevator.floor, step_containers)
    best_step_containers = path_container.get_best_step_containers()
    max_points = path_container.get_full_points(best_step_containers)
    target_floor = best_step_containers[0].floor

    #best_path_container = BestPathContainer(current_tick, elevator.id, elevator.floor, False, best_step_containers)
    #json_file = path_container.to_json()
    #path_containers_to_save += [json_file]

    return target_floor, max_points


class Strategy(BaseStrategy):
    @staticmethod
    def update_elevators(my_elevators, enemy_elevators):
        global CLOSE_OPEN_TIME
        global closing_elevators_time
        for e in my_elevators:
            if e.state == 4:
                if closing_elevators_time[e.id] == 0:
                    closing_elevators_time[e.id] = CLOSE_OPEN_TIME
                else:
                    closing_elevators_time[e.id] -= 1
            else:
                closing_elevators_time[e.id] = 0

        for e in enemy_elevators:
            if e.state == 4:
                if closing_elevators_time[e.id] == 0:
                    closing_elevators_time[e.id] = CLOSE_OPEN_TIME
                else:
                    closing_elevators_time[e.id] -= 1
            else:
                closing_elevators_time[e.id] = 0

    @staticmethod
    def update_passengers_owner(my_passengers, enemy_passengers, my_elevators):
        global is_self_passengers
        for p in my_passengers:
            if p.state == 5:  # если пассажир едет на лифте, проверяем, на каком
                is_self_passengers[p.id] = len([e for e in my_elevators if e.id == p.elevator]) > 0
            else:
                is_self_passengers[p.id] = True

        for p in enemy_passengers:
            if p.state == 5:  # если пассажир едет на лифте, проверяем, на каком
                is_self_passengers[p.id] = len([e for e in my_elevators if e.id == p.elevator]) > 0
            else:
                is_self_passengers[p.id] = False

    @staticmethod
    def update_passengers(my_passengers, enemy_passengers, my_elevators, enemy_elevators):
        global all_passengers
        global walking_passengers
        global FLOOR_WALKING_TIME
        global STAIRWAY_SPEED_DOWN
        global STAIRWAY_SPEED_UP
        global is_self_passengers
        global DELAY_FLOOR_TIME

        # добавляем или обновляем пассажира с этажом
        for p in my_passengers:
            all_passengers[p.id] = p.dest_floor
        for p in enemy_passengers:
            all_passengers[p.id] = p.dest_floor

        # удаляем из словаря гуляющих тех, кто появился на этаже и ждет лифт (или идет к нему, или возвращается)
        deleting_keys = [key for key in walking_passengers.keys() if
                         (len([x for x in my_passengers if x.id == key and x.state <= 3]) > 0 or
                          len([x for x in enemy_passengers if x.id == key and x.state <= 3]) > 0)]
        for key in deleting_keys:
            del walking_passengers[key]

        for key in all_passengers.keys():
            my_pass = [x for x in my_passengers if x.id == key]
            enemy_pass = [x for x in enemy_passengers if x.id == key]
            passenger = None
            if len(my_pass) > 0:
                passenger = my_pass[0]
            elif len(enemy_pass) > 0:
                passenger = enemy_pass[0]

            # его нет среди пассажиров - гуляет по этажу (или выходит из лифта)
            if passenger is None or passenger.state == 6:
                # уменьшаем время гуляния на 1
                if key in walking_passengers.keys():
                    walking_passengers[key] -= 1
                    # TODO: walking_passengers[key] == 0:

            elif passenger.dest_floor == 1:  # Если целевой этаж =1, то пассажир исччезнет навсегда, приехав на него
                continue

            elif passenger.state == 5:  # едет в лифте
                elevator = get_passenger_elevator(passenger, my_elevators, enemy_elevators)

                # в состоянии 3 next_floor лифта может меняться
                # сойдет на этаже, куда едет лифт
                if elevator.state != 3 and passenger.dest_floor == elevator.next_floor:
                    time = get_time_to_floor_for_real_elevator(elevator)
                    time += DELAY_FLOOR_TIME  # Добавялем время высадки пассажира
                    # TODO: int округлит вниз - нормально ли это???
                    walking_passengers[key] = math.ceil(time + FLOOR_WALKING_TIME)

            elif passenger.state == 4:  # идет пешком
                time = get_time_to_floor_for_stairway(passenger)
                walking_passengers[key] = math.ceil(time + FLOOR_WALKING_TIME)

    @staticmethod
    def update_passengers_targets(my_passengers, enemy_passengers):
        global passengers_targets
        global passengers_steps
        for p in my_passengers:
            if p.id not in passengers_targets:
                passengers_targets[p.id] = [p.dest_floor]
                passengers_steps[p.id] = 0
            else:
                step = passengers_steps[p.id]
                if p.dest_floor != passengers_targets[p.id][step]:
                    passengers_steps[p.id] += 1
                    if len(passengers_targets[p.id]) <= passengers_steps[p.id]:
                        passengers_targets[p.id] += [p.dest_floor]
                        twin_id = p.id + 1 if p.id % 2 == 1 else p.id - 1
                        passengers_targets[twin_id] += [p.dest_floor]

        for p in enemy_passengers:
            if p.id not in passengers_targets:
                passengers_targets[p.id] = [p.dest_floor]
                passengers_steps[p.id] = 0
            else:
                step = passengers_steps[p.id]
                if p.dest_floor != passengers_targets[p.id][step]:
                    passengers_steps[p.id] += 1
                    if len(passengers_targets[p.id]) <= passengers_steps[p.id]:
                        passengers_targets[p.id] += [p.dest_floor]
                        twin_id = p.id + 1 if p.id % 2 == 1 else p.id - 1
                        passengers_targets[twin_id] += [p.dest_floor]

    def get_elevator_points(self, elevator, passengers, add_time):
        global FIRST_FLOOR
        global LAST_FLOOR
        global current_tick
        global GAME_TIME
        global EPS_TIME

        max_points = 0
        # is_critical = False

        for floor1 in range(FIRST_FLOOR, LAST_FLOOR + 1):
            if floor1 == elevator.floor:
                continue

            if len([p for p in passengers if p.dest_floor == floor1]) == 0:
                continue

            time1 = get_time_to_floor_for_virtual_elevator(elevator.floor, floor1, [p for p in passengers if p.state != 6])

            points1 = 0
            for p in [p for p in passengers if p.state != 6 and p.dest_floor == floor1]:
                one_pass_points = get_one_pass_points(p.from_floor, floor1)
                if p.type != elevator.type:
                    one_pass_points *= 2
                points1 += one_pass_points

            if points1 > max_points:
                if current_tick + time1 + add_time < GAME_TIME:
                    max_points = points1
                    # if current_tick + time1 + add_time + EPS_TIME > GAME_TIME:
                    #     is_critical = True
                    # else:
                    #     is_critical = False

            if current_tick + time1 < GAME_TIME:
                for floor2 in range(FIRST_FLOOR, LAST_FLOOR + 1):
                    if floor2 == elevator.floor or floor2 == floor1:
                        continue
                    if len([p for p in passengers if p.dest_floor == floor2]) == 0:
                        continue

                    time2 = time1 + get_time_to_floor_for_virtual_elevator(floor1, floor2,
                                                                   [p for p in passengers if p.state != 6 and p.dest_floor != floor1])

                    points2 = points1

                    for p in [p for p in passengers if p.state != 6 and p.dest_floor == floor2]:
                        one_pass_points = get_one_pass_points(p.from_floor, floor2)
                        if p.type != elevator.type:
                            one_pass_points *= 2
                        points2 += one_pass_points

                    if points2 > max_points:
                        if current_tick + time2 + add_time < GAME_TIME:
                            max_points = points2
                            # if current_tick + time2 + add_time + EPS_TIME > GAME_TIME:
                            #     is_critical = True
                            # else:
                            #     is_critical = False

        return max_points

    def need_finish_move(self, elevator, my_passengers, enemy_passengers):
        move_points = self.get_elevator_points(elevator, elevator.passengers, 0)

        passengers_by_time_to_me = {}
        for p in [p for p in my_passengers if p.state == 2 and p.elevator == elevator.id]:
            time = get_pass_elevator_time(p.x, elevator)
            if time not in passengers_by_time_to_me:
                passengers_by_time_to_me[time] = []
            passengers_by_time_to_me[time] += [p]

        for p in [p for p in enemy_passengers if p.state == 2 and p.elevator == elevator.id]:
            time = get_pass_elevator_time(p.x, elevator)
            if time not in passengers_by_time_to_me:
                passengers_by_time_to_me[time] = []
            passengers_by_time_to_me[time] += [p]

        passengers_by_time_to_me_list = []
        for key, value in passengers_by_time_to_me.items():
            passengers_by_time_to_me_list += [[key, value]]

        if len(passengers_by_time_to_me_list) == 0:
            return False

        ordered_passengers_by_time_to_me_list = sorted(passengers_by_time_to_me_list, key=lambda x: x[0], reverse=False)

        new_passengers = [p for p in elevator.passengers]
        for item in ordered_passengers_by_time_to_me_list:
            new_passengers += item[1]
            no_move_points = self.get_elevator_points(elevator, new_passengers, item[0])
            if no_move_points >= move_points:
                return False

        return True

    def need_move(self, elevator, my_passengers, enemy_passengers):
        global current_tick
        global PASS_CREATION_TIME
        global FIRST_FLOOR
        global waiting_elevators
        global EPS_TIME
        global GAME_TIME

        not_exiting_passengers = [p for p in elevator.passengers if p.dest_floor != elevator.floor]
        if len(not_exiting_passengers) == 20:
            return True

        if elevator.floor == FIRST_FLOOR and current_tick <= PASS_CREATION_TIME:
            return False

        is_time_finished = self.need_finish_move(elevator, my_passengers, enemy_passengers)
        if is_time_finished:
            self.debug("VALIM: " + str(elevator.id))
            return True

        ok_my_passengers = [p for p in my_passengers if
                            p.floor == elevator.floor and p.time_to_away >= get_pass_elevator_time(p.x, elevator) and
                            (p.state == 1 or p.state == 3 or p.state == 2 and p.elevator == elevator.id)]
        ok_enemy_passengers = [p for p in enemy_passengers if
                               p.floor == elevator.floor and p.time_to_away >= get_pass_elevator_time(p.x, elevator) and
                               (p.state == 1 or p.state == 3 or p.state == 2 and p.elevator == elevator.id)]

        # Если пассажиры есть, лифт лифт не ждет их появления и уезжать не надо
        no_passengers = len(ok_my_passengers) == 0 and len(ok_enemy_passengers) == 0
        if not no_passengers:
            waiting_elevators[elevator.id] = False
            return False
        # Если пассажиров нет, уедем, если лифт не ждет их появления
        return not waiting_elevators[elevator.id]

    def on_tick(self, my_elevators, my_passengers, enemy_elevators, enemy_passengers):
        global current_tick
        global FIRST_FLOOR
        global waiting_elevators
        global CLOSE_OPEN_TIME
        global DELAY_FLOOR_TIME
        global path_containers_to_save

        self.update_elevators(my_elevators, enemy_elevators)
        self.update_passengers_owner(my_passengers, enemy_passengers, my_elevators)
        self.update_passengers(my_passengers, enemy_passengers, my_elevators, enemy_elevators)
        self.update_passengers_targets(my_passengers, enemy_passengers)

        ok_my_passengers = [p for p in my_passengers if p.state <= 3]
        ok_enemy_passengers = [p for p in enemy_passengers if p.state <= 3]

        for elevator in [e for e in my_elevators if e.state == 3]:
            if elevator.time_on_floor >= CLOSE_OPEN_TIME + DELAY_FLOOR_TIME:
                if self.need_move(elevator, my_passengers, enemy_passengers):
                    target_floor, max_points = get_optimal_elevator_path(
                        elevator, my_passengers, enemy_passengers, my_elevators, enemy_elevators)
                    if target_floor == elevator.floor:
                        waiting_elevators[elevator.id] = True
                    elif target_floor != -1:
                        waiting_elevators[elevator.id] = False
                        elevator.go_to_floor(target_floor)

        for elevator in [e for e in my_elevators if e.state == 3]:
            if current_tick <= PASS_CREATION_TIME and elevator.floor == FIRST_FLOOR:
                call_start_ticks_passengers(elevator, ok_my_passengers, ok_enemy_passengers)
            else:
                call_passengers(elevator, ok_my_passengers, ok_enemy_passengers, enemy_elevators)

        current_tick += 1
        # if current_tick == 7200:
        #     f = open('best_path_container.json', 'w')
        #     for item in path_containers_to_save:
        #         f.write("%s\n" % item)
        #     f.close()
