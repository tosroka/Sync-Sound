class TagMatcher:
    def match(
        self, image_paths: list[str], available_tags: list[str], top_k: int = 5
    ) -> list[str]:
        """
        Takes a list of image paths (representing frames of a video)
        and a list of available tags to match against.

        Returns the top_k matching tags.
        """
        return []
