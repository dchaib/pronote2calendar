#!/bin/sh


if [ "$1" == "init" ]; then
    shift

    qr_code=""
    pin=""

    # Parse the arguments passed to the container
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            --qr_code)
                qr_code="$2"
                shift 2
                ;;
            --pin)
                pin="$2"
                shift 2
                ;;
            *)
                echo "Unknown argument: $1"
                exit 1
                ;;
        esac
    done

    if [[ -n "$qr_code" && -n "$pin" ]]; then
        python -m pronote2calendar.create_credentials --qr_code "$qr_code" --pin "$pin"
    else
        python -m pronotepy.create_login
    fi
else
    # For other commands, execute them normally
    exec "$@"
fi