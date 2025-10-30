from gpiozero import Servo
from time import sleep

def start_drilling():
    servo = Servo(13)
    # forward with rampup and ramp down
    servo.value = 0.9
    sleep(0.5)
    servo.max()
    sleep(48.2) #<--- 40 seconds
    servo.value = 0.9
    sleep(5)
    #45.5 seconds total runtime

    #pause
    servo.mid()
    sleep(1.0)

    # backwards with rampup and ramp down
    servo.value = -0.5
    sleep(0.5)
    servo.min()
    sleep(47.6) #<--- 40 seconds
    servo.value = -0.5
    sleep(5)
    # 44.5 seconds total runtime

    #stop
    servo.mid()
    servo.close()
    return