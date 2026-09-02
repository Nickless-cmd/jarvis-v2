/**
 * En ÆGTE assistent-tur, hentet fra /chat/sessions efter server-rettelsen
 * 2026-09-02. Teksten er afkortet; strukturen er urørt.
 *
 * Fixturen findes fordi et konstrueret eksempel ikke ville have fanget
 * fejlen: API'et sender content_json som et ARRAY, ikke som en JSON-streng,
 * og den antagelse væltede MessageList med «undefined is not a function».
 * Ægte data fanger den slags; opdigtede data bekræfter kun det man troede.
 */
export const REAL_TURN_BLOCKS: unknown[] = [
  {
    "type": "text",
    "text": "Vi starter med skridt 1 — læser fri diskplads på rodpartitio"
  },
  {
    "type": "tool_use",
    "name": "bash",
    "input": {
      "command": "df -h /"
    }
  },
  {
    "type": "tool_result"
  },
  {
    "type": "text",
    "text": "**1) Fri diskplads:** 20G fri på rodpartitionen (98G total, "
  },
  {
    "type": "tool_use",
    "name": "bash",
    "input": {
      "command": "hostname"
    }
  },
  {
    "type": "tool_result"
  },
  {
    "type": "text",
    "text": "**2) Værtsnavn:** `Jarvis` — passende nok. Nu tæller jeg fil"
  },
  {
    "type": "tool_use",
    "name": "bash",
    "input": {
      "command": "ls -1 /etc | wc -l"
    }
  },
  {
    "type": "tool_result"
  },
  {
    "type": "text",
    "text": "**3) Filer i /etc:** 189 stk.\n\nDe tre ting, i rækkefølge:\n\n1"
  },
  {
    "type": "progress"
  },
  {
    "type": "progress"
  },
  {
    "type": "progress"
  }
]
