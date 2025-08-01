#!/usr/bin/env python3

import sys
import tty
import termios
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
import time

class KeyboardVelocityPublisher(Node):
    def __init__(self):
        super().__init__('keyboard_velocity_publisher_node')
        
        # Publishers for velocity commands
        self.linear_pub = self.create_publisher(Float32, '/velocity', 10)
        self.angular_pub = self.create_publisher(Float32, '/angular_velocity', 10)
        
        # Velocity parameters
        self.linear_level = 0
        self.angular_level = 0
        self.step = 51  # Velocity step per level
        self.prev_key = ''
        
        self.show_instructions()
    
    def get_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def show_instructions(self):
        instructions = (
            "\n\n====== Keyboard Control Mode ======\n\n"
            "   [w] : Increase forward speed\n\n"
            "   [s] : Increase backward speed\n\n"
            "   [a] : Increase left turn (skid steer) speed\n\n"
            "   [d] : Increase right turn (skid steer) speed\n\n"
            "   [q] : Increase left turn (driff) speed\n\n"
            "   [e] : Increase right turn (driff) speed\n\n"
            "   [p] : STOP and exit\n\n"
            "-------------------------------------\n"
            f"Current speed: Linear={self.linear_level}, Angular={self.angular_level}\n"
        )
        self.get_logger().info(instructions)
    
    def calculate_and_publish_velocity(self, key):
        # Reset angular level if switching from linear movement
        if key in ['a', 'd'] and self.prev_key in ['w', 's']:
            self.angular_level = 0
        
        # Reset linear level if switching from angular movement
        if key in ['w', 's'] and self.prev_key in ['a', 'd']:
            self.linear_level = 0
        
        # Handle key presses
        if key == 'w':
            self.linear_level = min(5, self.linear_level + 1)
            self.angular_level = 0
        elif key == 's':
            self.linear_level = max(-5, self.linear_level - 1)
            self.angular_level = 0
        elif key == 'a':
            self.angular_level = max(-5, self.angular_level - 1)
            self.linear_level = 0
        elif key == 'd':
            self.angular_level = min(5, self.angular_level + 1)
            self.linear_level = 0
        else:
            return False
        
        self.prev_key = key
        
        # Create and publish velocity messages
        linear_speed = Float32()
        angular_speed = Float32()
        
        linear_speed.data = float(self.linear_level * self.step)
        angular_speed.data = float(self.angular_level * self.step)
        
        self.linear_pub.publish(linear_speed)
        self.angular_pub.publish(angular_speed)
        
        self.get_logger().info(
            f"[KEY:{key}] Linear: {linear_speed.data} | Angular: {angular_speed.data}"
        )
        
        return True
    
    def run(self):
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
            key = self.get_key().lower()
            
            if key == 'p':
                self.get_logger().info("STOP command received. Exiting...")
                break
            
            if key in ['w', 'a', 's', 'd']:
                if self.calculate_and_publish_velocity(key):
                    time.sleep(0.1)  # Small delay to prevent rapid key repeats

def main():
    rclpy.init()
    node = KeyboardVelocityPublisher()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        # Publish zero velocities before shutting down
        zero_vel = Float32()
        zero_vel.data = 0.0
        node.linear_pub.publish(zero_vel)
        node.angular_pub.publish(zero_vel)
        
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
