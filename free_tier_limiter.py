"""
Free Tier Protection System
Ensures the app never exceeds free tier limits
"""

import os
import json
from datetime import datetime, date
from functools import wraps
from collections import defaultdict
import time

class FreeTierLimiter:
    """Main class to manage all free tier limits"""
    
    # Define free tier limits
    LIMITS = {
        'upstash_redis': {
            'daily_requests': 10000,
            'warning_percent': 80
        },
        'render_hosting': {
            'monthly_hours': 750,
            'warning_percent': 85
        },
        'api_requests': {
            'daily_requests': 50000,  # Self-imposed to stay safe
            'warning_percent': 75
        },
        'database_queries': {
            'daily_requests': 5000,  # Conservative limit
            'warning_percent': 70
        }
    }
    
    def __init__(self):
        self.usage = defaultdict(lambda: defaultdict(int))
        self.last_reset = defaultdict(lambda: datetime.now())
        self.alerts_sent = set()
        self.degradation_mode = False
        
    def increment_usage(self, service, metric='requests'):
        """Increment usage counter for a service"""
        key = self._get_key(service, metric)
        self.usage[service][key] += 1
        
        # Check if we need to send alerts
        self._check_alerts(service)
        
        return self.usage[service][key]
    
    def check_limit(self, service, metric='requests'):
        """Check if we're within limits for a service"""
        current_usage = self.get_usage(service, metric)
        limit_config = self.LIMITS.get(service, {})
        
        if metric == 'daily_requests':
            limit = limit_config.get('daily_requests', float('inf'))
        elif metric == 'monthly_hours':
            limit = limit_config.get('monthly_hours', float('inf'))
        else:
            limit = float('inf')
            
        return current_usage < limit
    
    def get_usage(self, service, metric='requests'):
        """Get current usage for a service"""
        key = self._get_key(service, metric)
        return self.usage[service].get(key, 0)
    
    def get_usage_percentage(self, service):
        """Get usage as percentage of limit"""
        current = self.get_usage(service, 'requests')
        limit_config = self.LIMITS.get(service, {})
        
        if 'daily_requests' in limit_config:
            limit = limit_config['daily_requests']
        else:
            return 0
            
        return (current / limit * 100) if limit > 0 else 0
    
    def should_use_cache(self, service):
        """Determine if we should use cache based on usage"""
        usage_percent = self.get_usage_percentage(service)
        
        if usage_percent < 50:
            return False  # Normal operation
        elif usage_percent < 70:
            return True, 300  # 5 min cache
        elif usage_percent < 85:
            return True, 1800  # 30 min cache
        elif usage_percent < 95:
            return True, 3600  # 1 hour cache
        else:
            return True, 86400  # 24 hour cache
    
    def get_service_level(self):
        """Get current service level based on usage"""
        max_usage = max(
            self.get_usage_percentage(service) 
            for service in self.LIMITS.keys()
        )
        
        if max_usage < 70:
            return 'normal'
        elif max_usage < 85:
            return 'reduced'
        elif max_usage < 95:
            return 'minimal'
        else:
            return 'static_only'
    
    def _get_key(self, service, metric):
        """Get storage key for usage tracking"""
        if 'daily' in metric:
            return f"{metric}:{date.today()}"
        elif 'monthly' in metric:
            return f"{metric}:{datetime.now().strftime('%Y-%m')}"
        else:
            return metric
    
    def _check_alerts(self, service):
        """Check if we need to send usage alerts"""
        usage_percent = self.get_usage_percentage(service)
        limit_config = self.LIMITS.get(service, {})
        warning_percent = limit_config.get('warning_percent', 80)
        
        alert_key = f"{service}:{date.today()}:{warning_percent}"
        
        if usage_percent >= warning_percent and alert_key not in self.alerts_sent:
            self.alerts_sent.add(alert_key)
            self._send_alert(service, usage_percent)
    
    def _send_alert(self, service, usage_percent):
        """Send usage alert (implement your preferred method)"""
        alert_msg = f"⚠️ {service} at {usage_percent:.1f}% of free tier limit"
        print(f"ALERT: {alert_msg}")
        # TODO: Add Discord webhook, email, or other notification
    
    def get_all_usage_stats(self):
        """Get usage statistics for all services"""
        stats = {}
        for service, limits in self.LIMITS.items():
            usage = self.get_usage(service, 'requests')
            percentage = self.get_usage_percentage(service)
            
            stats[service] = {
                'current': usage,
                'limit': limits.get('daily_requests', 'N/A'),
                'percentage': percentage,
                'status': self._get_status(percentage),
                'service_level': self.get_service_level()
            }
        return stats
    
    def _get_status(self, percentage):
        """Get status based on usage percentage"""
        if percentage < 50:
            return 'healthy'
        elif percentage < 80:
            return 'warning'
        elif percentage < 95:
            return 'critical'
        else:
            return 'exceeded'


# Global limiter instance
limiter = FreeTierLimiter()


def rate_limit(service, bypass_for_cached=True):
    """Decorator to rate limit function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if we're within limits
            if not limiter.check_limit(service, 'daily_requests'):
                # Return cached response or error
                if bypass_for_cached and hasattr(func, '_cached_response'):
                    return func._cached_response
                else:
                    return {
                        'error': 'Daily limit exceeded',
                        'service': service,
                        'limit_reached': True
                    }, 429
            
            # Increment counter
            limiter.increment_usage(service, 'daily_requests')
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store as cached response for future limit exceeds
            func._cached_response = result
            
            return result
        return wrapper
    return decorator


def conditional_cache(service):
    """Decorator that adds caching based on usage"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if we should use cache
            should_cache = limiter.should_use_cache(service)
            
            if should_cache:
                cache_result, ttl = should_cache
                # TODO: Implement actual cache lookup
                # For now, just note that caching should be used
                kwargs['_cache_ttl'] = ttl
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class ServiceDegrader:
    """Handles graceful degradation of services"""
    
    @staticmethod
    def degrade_response(response, level):
        """Modify response based on degradation level"""
        if level == 'normal':
            return response
        elif level == 'reduced':
            # Limit response size
            if isinstance(response, list) and len(response) > 100:
                return response[:100]
            return response
        elif level == 'minimal':
            # Return only essential data
            if isinstance(response, list) and len(response) > 20:
                return response[:20]
            return response
        else:  # static_only
            # Return pre-computed static response
            return {
                'data': 'static_response',
                'degraded': True,
                'message': 'Service limit reached, showing cached data'
            }