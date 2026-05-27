"""
Go Scraper Pool - Load Balancer for Multiple Go Scraper Instances

Manages multiple Go scraper instances with intelligent load balancing.
Uses "least busy" strategy to distribute jobs across instances.
"""
import asyncio
from typing import Optional, List, Dict
import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class GoScraperPool:
    """
    Manages multiple Go scraper instances with load balancing.
    
    Uses "least busy" strategy to distribute jobs across instances:
    - Checks all instances for current load
    - Selects instance with fewest working jobs
    - Falls back to round-robin if health checks fail
    """
    
    def __init__(self):
        # List of Go scraper URLs (internal Docker network)
        self.instances = [
            "http://go_scraper_1:8080",
            "http://go_scraper_2:8080",
            "http://go_scraper_3:8080",
            "http://go_scraper_4:8080",
        ]
        self.current_index = 0
        self.timeout = settings.GO_SCRAPER_TIMEOUT
        self.poll_interval = settings.GO_SCRAPER_POLL_INTERVAL
    
    async def get_available_instance(self) -> Optional[str]:
        """
        Get an available Go scraper instance using round-robin + health check.
        
        Returns:
            URL of available instance, or None if all are busy/down
        """
        # Try each instance starting from current_index
        for i in range(len(self.instances)):
            index = (self.current_index + i) % len(self.instances)
            instance_url = self.instances[index]
            
            try:
                # Check if instance is healthy and has capacity
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{instance_url}/api/v1/jobs")
                    
                    if response.status_code == 200:
                        jobs = response.json() or []  # Handle None response
                        
                        # Count working jobs
                        working_count = sum(
                            1 for j in jobs
                            if j.get("Status") == "working" or j.get("status") == "working"
                        )
                        
                        # If instance has capacity (less than 2 working jobs)
                        if working_count < 2:
                            # Update index for next request
                            self.current_index = (index + 1) % len(self.instances)
                            
                            logger.info(
                                "pool.instance_selected",
                                instance=instance_url,
                                working_jobs=working_count,
                                index=index
                            )
                            
                            return instance_url
                        else:
                            logger.debug(
                                "pool.instance_busy",
                                instance=instance_url,
                                working_jobs=working_count
                            )
            
            except Exception as e:
                logger.warning(
                    "pool.instance_unhealthy",
                    instance=instance_url,
                    error=str(e)
                )
                continue
        
        # All instances are busy or down
        logger.warning("pool.all_instances_busy")
        return None
    
    async def get_least_busy_instance(self) -> Optional[str]:
        """
        Get the instance with the fewest working jobs.
        
        This is the RECOMMENDED strategy for production use.
        
        Returns:
            URL of least busy instance, or None if all are down
        """
        instance_loads: List[tuple[str, int]] = []
        
        for instance_url in self.instances:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{instance_url}/api/v1/jobs")
                    
                    if response.status_code == 200:
                        jobs = response.json() or []  # Handle None response
                        working_count = sum(
                            1 for j in jobs
                            if j.get("Status") == "working" or j.get("status") == "working"
                        )
                        instance_loads.append((instance_url, working_count))
            
            except Exception as e:
                logger.warning(
                    "pool.instance_check_failed",
                    instance=instance_url,
                    error=str(e)
                )
                continue
        
        if not instance_loads:
            logger.error("pool.all_instances_down")
            return None
        
        # Sort by load (ascending) and return least busy
        instance_loads.sort(key=lambda x: x[1])
        selected_instance, load = instance_loads[0]
        
        logger.info(
            "pool.least_busy_selected",
            instance=selected_instance,
            working_jobs=load,
            total_checked=len(instance_loads),
            all_loads=[(url.split("_")[-1].split(":")[0], count) for url, count in instance_loads]
        )
        
        return selected_instance
    
    async def get_all_queue_status(self) -> Dict:
        """
        Get queue status from all instances.
        
        Returns:
            Combined queue status from all instances
        """
        total_pending = 0
        total_working = 0
        total_completed = 0
        total_failed = 0
        instance_status = []
        
        for instance_url in self.instances:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{instance_url}/api/v1/jobs")
                    
                    if response.status_code == 200:
                        jobs = response.json() or []  # Handle None response
                        
                        pending = sum(1 for j in jobs if j.get("Status") == "pending" or j.get("status") == "pending")
                        working = sum(1 for j in jobs if j.get("Status") == "working" or j.get("status") == "working")
                        completed = sum(1 for j in jobs if j.get("Status") == "ok" or j.get("status") == "ok")
                        failed = sum(1 for j in jobs if j.get("Status") == "failed" or j.get("status") == "failed")
                        
                        total_pending += pending
                        total_working += working
                        total_completed += completed
                        total_failed += failed
                        
                        instance_status.append({
                            "instance": instance_url,
                            "status": "healthy",
                            "pending": pending,
                            "working": working,
                            "completed": completed,
                            "failed": failed,
                            "total": len(jobs)
                        })
            
            except Exception as e:
                instance_status.append({
                    "instance": instance_url,
                    "status": "unhealthy",
                    "error": str(e)
                })
        
        return {
            "total_instances": len(self.instances),
            "healthy_instances": sum(1 for s in instance_status if s.get("status") == "healthy"),
            "total_pending": total_pending,
            "total_working": total_working,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "instances": instance_status
        }
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        Check health of all instances.
        
        Returns:
            Dict mapping instance URL to health status (True/False)
        """
        health_status = {}
        
        for instance_url in self.instances:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{instance_url}/")
                    health_status[instance_url] = response.status_code == 200
            except Exception:
                health_status[instance_url] = False
        
        return health_status


# Global pool instance
go_scraper_pool = GoScraperPool()
