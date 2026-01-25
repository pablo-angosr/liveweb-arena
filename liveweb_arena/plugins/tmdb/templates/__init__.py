"""TMDB question templates"""

# Active templates with lower memorization risk
from .movie_crew import TMDBMovieCrewTemplate  # Cinematographers, editors, etc. - less famous

# Anti-memorization templates (recommended for evaluation)
from .person_filmography import TMDBPersonFilmographyTemplate
from .movie_collection import TMDBMovieCollectionTemplate
from .aggregate import TMDBAggregateTemplate
from .cast_position import TMDBCastPositionTemplate  # "5th billed actor" - hard to memorize
from .recent_works import TMDBRecentWorksTemplate    # Dynamic data

__all__ = [
    # Active (lower risk)
    "TMDBMovieCrewTemplate",
    # Recommended (anti-memorization)
    "TMDBPersonFilmographyTemplate",
    "TMDBMovieCollectionTemplate",
    "TMDBAggregateTemplate",
    "TMDBCastPositionTemplate",
    "TMDBRecentWorksTemplate",
]
