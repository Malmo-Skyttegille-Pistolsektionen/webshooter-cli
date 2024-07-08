class SingletonMeta(type):
    """
    A metaclass that ensures a class only has one instance (Singleton pattern).

    This is achieved by storing instances in a class-level dictionary and returning
    the existing instance if the class has already been instantiated.

    Attributes:
        _instances (dict): A dictionary to store the single instances of classes using this metaclass.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Controls the instantiation of the class.

        If the class has not been instantiated yet, it creates a new instance, stores it in the `_instances` dictionary,
        and returns it. If the class has already been instantiated, it returns the existing instance.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            object: The single instance of the class.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
