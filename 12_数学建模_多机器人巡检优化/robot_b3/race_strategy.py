from .posterior import best_clear_disk,posterior_cloud
from .score_strategy import ScoreStrategy


class RaceStrategy(ScoreStrategy):
    probability_threshold=.62
    max_statistical_attempts=2

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.mode='race'
        self.negative={c:[] for c in range(1,21)}
        self.failed_centers={c:[] for c in range(1,21)}
        self.race_attempts={}

    def _measure(self,q,c):
        result=super()._measure(q,c)
        if result=='no_signal':self.negative[c].append(tuple(q))
        return result

    def _clear(self,q,c):
        ok=super()._clear(q,c)
        if not ok:self.failed_centers[c].append(tuple(q))
        return ok

    def _posterior(self,c):
        cloud=posterior_cloud(self.observations.get(c,()),self.negative[c],self.failed_centers[c])
        return (*best_clear_disk(cloud),len(cloud))

    def _task_point(self,c):
        center,probability,count=self._posterior(c)
        return center if center is not None and probability>=.25 and count>=5 else super()._task_point(c)

    def _service(self,c,destination):
        _,radius=self._circle(c)
        if radius<=19.5:return super()._service(c,destination)
        center,probability,count=self._posterior(c)
        attempts=self.race_attempts.get(c,0)
        if (center is not None and count>=5 and probability>=self.probability_threshold
                and attempts<self.max_statistical_attempts):
            self.race_attempts[c]=attempts+1
            if self._clear(center,c):return
            if self._time_ok():self._measure(self.position,c)
            return
        return super()._service(c,destination)
