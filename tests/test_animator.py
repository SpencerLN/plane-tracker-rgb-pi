"""Tests for the animator utility module."""

import pytest
import sys
from pathlib import Path

# Ensure conftest.py is loaded first
sys.path.insert(0, str(Path(__file__).parent))


class TestAnimatorKeyFrame:
    """Test the Animator.KeyFrame decorator."""
    
    def test_keyframe_properties_added(self):
        """Test that KeyFrame.add adds properties to methods."""
        from utilities.animator import Animator
        
        @Animator.KeyFrame.add(divisor=5, offset=2)
        def test_method(count):
            pass
        
        assert hasattr(test_method, 'properties')
        assert test_method.properties['divisor'] == 5
        assert test_method.properties['offset'] == 2
        assert test_method.properties['count'] == 0
    
    def test_keyframe_default_offset(self):
        """Test that KeyFrame.add has default offset of 0."""
        from utilities.animator import Animator
        
        @Animator.KeyFrame.add(divisor=10)
        def test_method(count):
            pass
        
        assert test_method.properties['offset'] == 0


class TestAnimator:
    """Test the Animator base class."""
    
    def test_animator_initialization(self):
        """Test that Animator initializes correctly."""
        from utilities.animator import Animator, DELAY_DEFAULT
        
        animator = Animator()
        
        assert animator.frame == 0
        assert animator.delay == DELAY_DEFAULT
        assert isinstance(animator.keyframes, list)
    
    def test_delay_property(self):
        """Test delay getter and setter."""
        from utilities.animator import Animator
        
        animator = Animator()
        animator.delay = 0.05
        
        assert animator.delay == 0.05
    
    def test_keyframe_registration(self):
        """Test that decorated methods are registered as keyframes."""
        from utilities.animator import Animator
        
        class TestClass(Animator):
            @Animator.KeyFrame.add(1)
            def method_a(self, count):
                pass
            
            @Animator.KeyFrame.add(5)
            def method_b(self, count):
                pass
        
        test_obj = TestClass()
        
        # Should have both methods registered
        method_names = [kf.__name__ for kf in test_obj.keyframes]
        assert 'method_a' in method_names
        assert 'method_b' in method_names
    
    def test_reset_scene_calls_zero_divisor_keyframes(self):
        """Test that reset_scene calls all keyframes with divisor=0."""
        from utilities.animator import Animator
        
        call_log = []
        
        class TestClass(Animator):
            @Animator.KeyFrame.add(0)
            def setup_method(self):
                call_log.append('setup')
            
            @Animator.KeyFrame.add(1)
            def regular_method(self, count):
                call_log.append('regular')
        
        test_obj = TestClass()
        call_log.clear()  # Clear calls from __init__
        
        test_obj.reset_scene()
        
        assert 'setup' in call_log
        assert 'regular' not in call_log
