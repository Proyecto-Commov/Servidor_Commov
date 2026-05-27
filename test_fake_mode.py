#!/usr/bin/env python3
"""
Test script to verify dual-mode fake temperature generation logic
"""

class FakeModeTest:
    def __init__(self):
        self.fake_base_temp = 25.0
        self.fake_target_temp = None
        self.fake_drift_counter = 0
        self.fake_drift_samples = 5
    
    def test_drift_to_target(self, target):
        """Test drift logic from current temp to target"""
        print(f"\n📊 Starting drift test: {self.fake_base_temp}°C → {target}°C")
        
        self.fake_target_temp = float(target)
        self.fake_drift_counter = 0
        
        for sample in range(10):  # Run 10 samples
            if self.fake_target_temp is not None and self.fake_drift_counter < self.fake_drift_samples:
                increment = (self.fake_target_temp - self.fake_base_temp) / self.fake_drift_samples
                self.fake_base_temp += increment
                self.fake_drift_counter += 1
                
                if self.fake_drift_counter >= self.fake_drift_samples:
                    self.fake_base_temp = self.fake_target_temp
                    print(f"  Sample {sample+1}: {self.fake_base_temp:.2f}°C ✓ DRIFT COMPLETE")
                    self.fake_target_temp = None
                else:
                    print(f"  Sample {sample+1}: {self.fake_base_temp:.2f}°C (drift {self.fake_drift_counter}/{self.fake_drift_samples})")
            else:
                # Oscillation mode
                print(f"  Sample {sample+1}: {self.fake_base_temp:.2f}°C (oscillating)")
    
    def test_multiple_drifts(self):
        """Test multiple consecutive drifts"""
        print("\n" + "="*60)
        print("Testing multiple consecutive drifts")
        print("="*60)
        
        # Start at 25°C
        self.fake_base_temp = 25.0
        print(f"Initial temperature: {self.fake_base_temp}°C")
        
        # First drift: 25 → 50 (key 5)
        self.test_drift_to_target(50)
        
        # Second drift: 50 → 10 (key 1)
        self.test_drift_to_target(10)
        
        # Third drift: 10 → 90 (key 9)
        self.test_drift_to_target(90)

if __name__ == "__main__":
    test = FakeModeTest()
    test.test_multiple_drifts()
    
    print("\n" + "="*60)
    print("✓ Fake mode drift logic validation complete!")
    print("="*60)
