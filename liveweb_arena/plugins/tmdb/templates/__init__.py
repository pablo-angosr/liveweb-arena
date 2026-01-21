"""TMDB question templates"""

from .movie_info import TMDBMovieInfoTemplate
from .movie_cast import TMDBMovieCastTemplate
from .movie_comparison import TMDBMovieComparisonTemplate
from .person_filmography import TMDBPersonFilmographyTemplate
from .movie_crew import TMDBMovieCrewTemplate
from .movie_collection import TMDBMovieCollectionTemplate

__all__ = [
    "TMDBMovieInfoTemplate",
    "TMDBMovieCastTemplate",
    "TMDBMovieComparisonTemplate",
    "TMDBPersonFilmographyTemplate",
    "TMDBMovieCrewTemplate",
    "TMDBMovieCollectionTemplate",
]
