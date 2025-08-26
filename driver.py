import msgParser
import carState
import carControl
import csv
import os
import pygame
from datetime import datetime

class Driver(object):
    '''
    A driver object for the SCRC with optional Pygame-based control
    '''

    def __init__(self, stage, logfile=None, track_name=None, car_name=None, enable_logging=False, control_mode='ai'):
        '''Constructor'''
        self.WARM_UP = 0
        self.QUALIFYING = 1
        self.RACE = 2
        self.UNKNOWN = 3
        self.stage = stage
        self.logfile = logfile
        self.track_name = track_name
        self.car_name = car_name
        
        self.parser = msgParser.MsgParser()
        self.state = carState.CarState()
        self.control = carControl.CarControl()
        
        self.steer_lock = 0.785398
        self.max_speed = 100
        self.prev_rpm = None
        
        # Control mode selection
        self.control_modes = ['ai', 'kb', 'controller']
        if control_mode not in self.control_modes:
            raise ValueError(f"Control mode must be one of {self.control_modes}")
        self.control_mode = control_mode
        
        # Pygame initialization for human control
        if self.control_mode in ['kb', 'controller']:
            pygame.init()
            pygame.display.set_mode((400, 300))  # Always needed for key/controller
            pygame.display.set_caption("TORCS Control")

            if self.control_mode == 'controller':
                pygame.joystick.init()
                if pygame.joystick.get_count() > 0:
                    self.joystick = pygame.joystick.Joystick(0)
                    self.joystick.init()
                    print(f"Controller detected: {self.joystick.get_name()}")
                else:
                    print("No controller detected, falling back to keyboard")
                    self.control_mode = 'kb'

        
        self.enable_logging = enable_logging
        if self.enable_logging:
            # Create logs directory if it doesn't exist
            self.logs_dir = "logs"
            os.makedirs(self.logs_dir, exist_ok=True)
            
            # Generate filename with current timestamp and control mode
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if(self.control_mode in ['kb', 'controller']):
                self.log_file = os.path.join(self.logs_dir, f"sensor_log_{timestamp}_human.csv")
            else:
                self.log_file = os.path.join(self.logs_dir, f"sensor_log_{timestamp}_ai.csv")
            self.init_log()
            
            # For keypress/controller input logging
            self.current_inputs = set()

    def init_log(self):
        '''Initialize the CSV log file with headers for all sensors and keypresses'''
        with open(self.log_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Write headers for all available sensors
            writer.writerow([
                'timestamp',
                'angle',
                'curLapTime',
                'damage',
                'distFromStart',
                'distRaced',
                'fuel',
                'gear',
                'lastLapTime',
                'racePos',
                'rpm',
                'speedX',
                'speedY',
                'speedZ',
                'trackPos',
                'z',
                # Array-type sensors will be flattened
                *[f'focus_{i}' for i in range(5)],
                *[f'opponent_{i}' for i in range(36)],
                *[f'track_{i}' for i in range(19)],
                *[f'wheelSpinVel_{i}' for i in range(4)],
                # Control outputs
                'accel',
                'brake',
                'clutch',
                'steer',
                # Inputs
                'inputs'
            ])

    def log_sensors(self):
        '''Log all sensor data to the CSV file'''
        with open(self.log_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            # Flatten array-type sensors
            focus = self.state.focus if self.state.focus is not None else [None]*5
            opponents = self.state.opponents if self.state.opponents is not None else [None]*36
            track = self.state.track if self.state.track is not None else [None]*19
            wheelSpinVel = self.state.wheelSpinVel if self.state.wheelSpinVel is not None else [None]*4
            
            # Convert current inputs to string representation
            input_str = ','.join(sorted(self.current_inputs)) if self.current_inputs else 'None'
            
            # Write all sensor data
            writer.writerow([
                datetime.now().isoformat(),
                self.state.angle,
                self.state.curLapTime,
                self.state.damage,
                self.state.distFromStart,
                self.state.distRaced,
                self.state.fuel,
                self.state.gear,
                self.state.lastLapTime,
                self.state.racePos,
                self.state.rpm,
                self.state.speedX,
                self.state.speedY,
                self.state.speedZ,
                self.state.trackPos,
                self.state.z,
                # Flatten array sensors
                *focus,
                *opponents,
                *track,
                *wheelSpinVel,
                # Control outputs
                self.control.getAccel(),
                self.control.getBrake(),
                self.control.getClutch(),
                self.control.getSteer(),
                # Inputs
                input_str
            ])
            
            # Reset inputs for next frame
            self.current_inputs = set()

    def init(self):
        '''Return init string with rangefinder angles'''
        self.angles = [0 for x in range(19)]
        
        for i in range(5):
            self.angles[i] = -90 + i * 15
            self.angles[18 - i] = 90 - i * 15
        
        for i in range(5, 9):
            self.angles[i] = -20 + (i-5) * 5
            self.angles[18 - i] = 20 - (i-5) * 5
        
        return self.parser.stringify({'init': self.angles})
    
    def human_control(self):
        '''Handle human keyboard controls using Pygame'''


        pygame.event.pump()
        # Get pressed keys
        keys = pygame.key.get_pressed()
        
        # Track inputs for logging
        self.current_inputs = set()
        
        # Steering
        if keys[pygame.K_LEFT]:
            self.control.setSteer(1.0)  # Full left
            self.current_inputs.add('LEFT')
        elif keys[pygame.K_RIGHT]:
            self.control.setSteer(-1.0)  # Full right
            self.current_inputs.add('RIGHT')
        else:
            self.control.setSteer(0)  # Neutral steering
        
        # Acceleration
        if keys[pygame.K_UP]:
            self.control.setAccel(1.0)  # Full acceleration
            self.control.setBrake(0)
            self.current_inputs.add('UP')
        elif keys[pygame.K_DOWN]:
            self.control.setAccel(0)
            self.control.setBrake(1.0)  # Full brake
            self.current_inputs.add('DOWN')
        else:
            self.control.setAccel(0)
            self.control.setBrake(0)
        
        # Gear shifting
        if keys[pygame.K_z]:
            self.control.setGear(self.state.getGear() - 1)  # Shift down
            self.current_inputs.add('Z')
        elif keys[pygame.K_x]:
            self.control.setGear(self.state.getGear() + 1)  # Shift up
            self.current_inputs.add('X')
        
        # Event handling to allow quitting
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
            elif event.type == pygame.KEYDOWN:
                # Add any other keypresses we want to track
                if event.key == pygame.K_SPACE:
                    self.current_inputs.add('SPACE')
                elif event.key == pygame.K_ESCAPE:
                    self.current_inputs.add('ESC')
    
    def controller_control(self):
        '''Handle Xbox 360 controller input'''
        # Process events to keep the controller state updated
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
        
        # Track inputs for logging
        self.current_inputs = set()
        
        if pygame.joystick.get_count() > 0:
            # Left stick (axis 0) for steering
            steer_axis = -self.joystick.get_axis(0)
            self.control.setSteer(steer_axis)
            if abs(steer_axis) > 0.1:
                self.current_inputs.add(f'STEER_{steer_axis:.2f}')
            
            # Right trigger (axis 5) for acceleration
            # Note: Xbox 360 triggers range from -1 (released) to 1 (pressed)
            # But some systems might report them as 0 to 1
            accel = (self.joystick.get_axis(5) + 1) / 2  # Normalize to 0-1
            self.control.setAccel(accel)
            if accel > 0.1:
                self.current_inputs.add(f'ACCEL_{accel:.2f}')
            
            # Left trigger (axis 4) for brake
            brake = (self.joystick.get_axis(4) + 1) / 2  # Normalize to 0-1
            self.control.setBrake(brake)
            if brake > 0.1:
                self.current_inputs.add(f'BRAKE_{brake:.2f}')
            
            # A button (button 0) for gear up
            if self.joystick.get_button(0):
                self.control.setGear(self.state.getGear() + 1)
                self.current_inputs.add('GEAR_UP')
            
            # B button (button 1) for gear down
            if self.joystick.get_button(1):
                self.control.setGear(self.state.getGear() - 1)
                self.current_inputs.add('GEAR_DOWN')
            
            
    
    def drive(self, msg):
        self.state.setFromMsg(msg)
        if self.control_mode == 'kb':
            self.human_control()
            
        elif self.control_mode == 'controller':
            self.controller_control()
        else:
            # Original AI driving logic
            self.steer()
            self.gear()
            self.speed()
        
        if self.enable_logging:
            self.log_sensors()
        
        return self.control.toMsg()
    
    def steer(self):
        angle = self.state.angle
        dist = self.state.trackPos
        self.control.setSteer((angle - dist*0.5)/self.steer_lock)
    
    def gear(self):
        rpm = self.state.getRpm()
        gear = self.state.getGear()
        
        if self.prev_rpm == None:
            up = True
        else:
            if (self.prev_rpm - rpm) < 0:
                up = True
            else:
                up = False
        
        if up and rpm > 7000:
            gear += 1
        
        if not up and rpm < 3000:
            gear -= 1
        
        self.control.setGear(gear)
    
    def speed(self):
        speed = self.state.getSpeedX()
        accel = self.control.getAccel()
        
        if speed < self.max_speed:
            accel += 0.1
            if accel > 1:
                accel = 1.0
        else:
            accel -= 0.1
            if accel < 0:
                accel = 0.0
        
        self.control.setAccel(accel)
            
    def onShutDown(self):
        if self.control_mode in ['kb', 'controller']:
            pygame.quit()
    
    def onRestart(self):
        pass