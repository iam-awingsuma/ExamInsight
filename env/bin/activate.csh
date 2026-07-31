# This file must be used with "source bin/activate.csh" *from csh*.

# Defines deactivate alias to restore original PATH, prompt, and environment variables
alias deactivate 'test $?_OLD_VIRTUAL_PATH != 0 && setenv PATH "$_OLD_VIRTUAL_PATH" && unset _OLD_VIRTUAL_PATH; rehash; test $?_OLD_VIRTUAL_PROMPT != 0 && set prompt="$_OLD_VIRTUAL_PROMPT" && unset _OLD_VIRTUAL_PROMPT; unsetenv VIRTUAL_ENV; test "\!:*" != "nondestructive" && unalias deactivate'

# Cleans up pre-existing environment variables non-destructively
deactivate nondestructive

# Sets the virtual environment base path variable
setenv VIRTUAL_ENV "/Users/awingsuma/Downloads/repos/ExamInsight/env"

# Saves current PATH and prepends virtual environment bin directory
set _OLD_VIRTUAL_PATH="$PATH"
setenv PATH "$VIRTUAL_ENV/bin:$PATH"

# Saves original shell prompt
set _OLD_VIRTUAL_PROMPT="$prompt"

# Prepends (env) to shell prompt unless explicitly disabled
if (! "$?VIRTUAL_ENV_DISABLE_PROMPT") then
    set prompt = "(env) $prompt"
endif

# Aliases pydoc to run via the environment's Python module
alias pydoc python -m pydoc

# Re-indexes executable commands in shell hash table
rehash
