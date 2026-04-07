from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedAction:
    verb: str
    target: str
    is_valid: bool


def parse_action(action_input):
    try:
        # Already structured -> return
        if isinstance(action_input, dict):
            return action_input

        # STRING FORMAT SUPPORT
        if isinstance(action_input, str):
            parts = action_input.strip().split()

            if len(parts) >= 2:
                action_type = parts[0]
                target = parts[1]

                return {
                    "action_type": action_type,
                    "target_alert_id": target,
                    "rationale_tag": "auto_parsed",
                }

        # fallback invalid
        return {"action_type": "noop", "rationale_tag": "invalid"}

    except Exception:
        return {"action_type": "noop", "rationale_tag": "exception"}


def parse_message_to_action(message: str) -> ParsedAction:
    try:
        if not isinstance(message, str):
            return ParsedAction(verb="invalid", target="", is_valid=False)

        text = message.strip()
        if not text:
            return ParsedAction(verb="invalid", target="", is_valid=False)

        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        target = parts[1].strip() if len(parts) > 1 else ""

        if command in {"investigate", "block", "resolve"} and target:
            return ParsedAction(verb=command, target=target, is_valid=True)

        if command == "block_ip" and target:
            return ParsedAction(verb="block", target=target, is_valid=True)

        return ParsedAction(verb="invalid", target=target, is_valid=False)
    except Exception:
        return ParsedAction(verb="invalid", target="", is_valid=False)
