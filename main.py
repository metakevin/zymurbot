import panel

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brew server")
    parser.add_argument('-f', '--functions', choices=["temp"], action="append",
                        help="functions to perform")
    args = parser.parse_args()

    if "temp" in args.actions:
        do_temp()


        
