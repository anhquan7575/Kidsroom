import sys


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        from kidsroom.diagnostics import self_test

        raise SystemExit(self_test(sys.argv[2]))
    from kidsroom.app import main

    main()
