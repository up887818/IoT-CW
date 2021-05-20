# up887818
# IOT Coursework - Creating IOT Application for Video Game Controller
# Main Code

# algorithm imports
import cv2
import mediapipe as mp
import math
# communication imports
import socket

# global variables
# origins[0] is left, origins[1] is right
origins = [(-1, -1), (-1, -1)]
# held_button[0] is left, held_button[1] is right
# using "17" as placeholder as only 16 buttons
held_button = [17, 17]
previous_location = [(0.5, 0.5), (0.5, 0.5)]

inner_annulus = ["TRIANGLE", "RIGHT", "CIRCLE", "DOWN",
                 "CROSS", "LEFT", "SQUARE", "UP"]
outer_annulus = ["OPTIONS", "R2", "R1", "PS",
                 "TOUCHPAD", "L1", "L2", "SHARE"]


# subroutines
def button_mode(landmarks, hand, palm):
    # clear origin from joystick mode
    origins[hand] = (-1, -1)

    movement = line_distance([previous_location[hand][0], palm[0]],
                            [previous_location[hand][1], palm[1]])

    # press button if hand moved, 0.05 seems reasonable to avoid tremors
    # causing accidental movements
    if movement >= 0.05:
        previous_location[hand] = palm
        # check hand's radius (distance) from global origin
        radius = line_distance([0.5, palm[0]], [0.5, palm[1]])
        print(radius)

        if (radius >= 0.25):
            # check how many degrees from north hand is
            change_x = palm[0] - 0.5
            change_y = 0.5 - palm[1]
            degrees = math.degrees(math.atan2(change_x, change_y))
            if degrees < 0:
                degrees += 360
            print(degrees)

            if radius < 0.375:
                # inner annulus
                button = int(degrees // 45)
                button_name = inner_annulus[button]

            else:
                # outer annulus
                button = int(degrees // 45)
                button_name = outer_annulus[int(degrees // 45)]

                button = button + 8

        else:
            button = 17

        held_button[hand] = button
        print(button)

        send = "B{}{}".format(hand, button)
        # B = button
        s.send(bytes(send, "UTF-8"))


def joystick_mode(landmarks, hand, palm):
    # if origin not yet defined, define it
    if origins[hand] == (-1, -1):
        origins[hand] = palm
        # remove held button
        # & set previous position to origin
        held_button[hand] = 17
        previous_location[hand] = (0.5, 0.5)
        update_button(hand)

    # else determine distance between centre and current position
    else:
        change_x = palm[0] - origins[hand][0]
        x = get_axis_value(change_x)

        change_y = origins[hand][1] - palm[1]
        y = get_axis_value(change_y)

        print("x: {} y: {}".format(x,y))

        send = "J{}{}y{}".format(hand, x, y)
        # J = joystick
        # y splits x and y values
        s.send(bytes(send,"UTF-8"))


def update_button(hand):
    # remove held button
    send = "U{}".format(hand)
    # U = update, then hand value
    s.send(bytes(send,"UTF-8"))


def hand_details(landmarks, two_hands):

    frame_landmarks = get_frame_coords(landmarks)
    # stops error if part of hand out of frame
    if len(frame_landmarks) >= 20:
        open = check_if_hand_open(frame_landmarks)
        hand = check_left_right(frame_landmarks[:2])
        centre = get_palm_centre(frame_landmarks[0], frame_landmarks[5],
                             frame_landmarks[17])

        if not two_hands:
            # remove potential button held by missing hand
            # abs(1-0) = 0, abs(0-1) = 1
            other_hand = abs(hand - 1)
            held_button[other_hand] = 17
            update_button(other_hand)

        if open:
            print("{} hand is open".format(hand))
            joystick_mode(frame_landmarks, hand, centre)

        else:
            print("{} hand is closed".format(hand))
            button_mode(frame_landmarks, hand, centre)

    else:
        print("Hand partially out of frame, can't find variables")


def get_frame_coords(landmarks):
    frame_landmarks = []

    for point in mp_hands.HandLandmark:
        normalised = landmarks.landmark[point]
        pixel_coord =\
        mp_drawing._normalized_to_pixel_coordinates(normalised.x, normalised.y,
                                                    image_width, image_height)

        try:
            frame_coord = ((pixel_coord[0] / image_width),
                          (pixel_coord[1] / image_height))

            frame_landmarks.append(frame_coord)

        # stop error from hand being partically out of frame. sometimes this
        # is not an issue, sometimes it is later on - this depends what
        # landmarks are missing - hence there's a length check in hand_details
        except TypeError:
            pass

    return frame_landmarks


def get_palm_centre(bottom, side_1, side_2):
    # 0 = bottom, 5 = edge 1, 17 = edge 2
    avg_x = (bottom[0] + side_1[0] + side_2[0])/3
    avg_y = (bottom[1] + side_1[1] + side_2[1])/3

    return (avg_x, avg_y)


def check_if_hand_open(landmarks):
    # 0 = index, 1 = middle,  2 = ring, 3 = pinky
    pip = [landmarks[6], landmarks[10],
            landmarks[14], landmarks[18]]
    dip = [landmarks[7], landmarks[11],
            landmarks[15], landmarks[19]]

    for finger in range(4):
        if pip[finger][1] < dip[finger][1]:
            return False

    return True


def check_left_right(landmarks):
    # hand 1 = right, hand 0 = left
    if landmarks[0][0] > landmarks[1][0]:
        return 1
    else:
        return 0


def line_distance(x, y):
    a = max(x) - min(x)
    b = max(y) - min(y)
    c2 = (a+b) ** 2
    c = math.sqrt(c2)
    return abs(c)


def get_axis_value(change):
    value = 0
    if -0.25 < change and change < 0.25:
        value = change * 4
    else:
        if change < 0:
            value = -1

        else:
            value = 1
    # 2dp
    value = round(value, 2)
    return value * 100
    # gives output between -100 and 100


def get_overlay():
    ret, frame = camera.read()
    img = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
    h, w, _ = img.shape
    # get overlay, resize to fit height of background whilst matching
    # aspect ratio
    overlay = cv2.imread("layout.png")
    overlay_h, overlay_w, _ = overlay.shape
    percentage = h / overlay_h
    new_overlay_w = int(overlay_w * percentage)
    new_size = (new_overlay_w, h)
    overlay = cv2.resize(overlay, new_size)

    # now add transparent border so that width is same as background
    x_shift = (w - new_overlay_w) // 2
    overlay = cv2.copyMakeBorder(overlay, 0, 0, x_shift, x_shift,
                                cv2.BORDER_CONSTANT, value=(0,0,0,1))

    return overlay

# main section
# set up bluetooth
server_mac = "00:19:10:09:27:26"
port = 1
passkey = "1234"

# necessary as hc-06 by default needs passkey to connect
# kill any "bluetooth-agent" process that is already running, then start
# a new "bluetooth-agent" process which includes passkey
# subprocess.call("kill -9 `pidof bluetooth-agent`",shell=True)
# status = subprocess.call("bluetooth-agent " + passkey + " &",shell=True)

s = socket.socket(socket.AF_BLUETOOTH,
                 socket.SOCK_STREAM,
                 socket.BTPROTO_RFCOMM)
s.connect((server_mac, port))

# set up cv2 & mediapipe
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.75,
                       min_tracking_confidence=0.5)
camera = cv2.VideoCapture(0)

# get overlay using 1st frame
overlay = get_overlay()

# run application
while camera.isOpened():
    ret, frame = camera.read()

    img = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
    image_height, image_width, _ = img.shape

    img.flags.writeable = False
    results = hands.process(img)
    # Draw the hand annotations on the image for output.
    img.flags.writeable = True
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    added_img = cv2.addWeighted(img, 0.5, overlay, 0.5, 0)

    if results.multi_hand_landmarks:
        two_hands = len(results.multi_hand_landmarks) == 2
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(added_img, hand_landmarks,
                                      mp_hands.HAND_CONNECTIONS)

            hand_details(hand_landmarks, two_hands)

    else:
        # no hands visible, remove button presses
        held_button = [17, 17]
        update_button(0)
        update_button(1)

    cv2.imshow('Controller', added_img)

    if cv2.waitKey(10) == 27:
        # Esc key to close
        break

# end program
hands.close() # mediapipe
camera.release() # cv2
cv2.destroyAllWindows() # cv2
s.close() # bluetooth
