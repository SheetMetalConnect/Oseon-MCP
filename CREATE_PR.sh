#!/bin/bash
# Create Pull Request for v2.0.0

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Creating Pull Request for v2.0.0${NC}\n"

# Branch info
BRANCH="claude/refactor-modular-mcp-server-011CUrVh2tNa854xM18cSQeL"

echo "Branch: $BRANCH"
echo "Target: main"
echo ""

# Get the PR description
if [ -f "PR_DESCRIPTION.md" ]; then
    echo -e "${GREEN}✓ PR Description ready${NC}"
    echo ""
    echo "To create the PR, visit:"
    echo "https://github.com/SheetMetalConnect/Oseon-MCP/pull/new/$BRANCH"
    echo ""
    echo "Or copy PR_DESCRIPTION.md content and paste it into GitHub's PR form."
else
    echo "Error: PR_DESCRIPTION.md not found"
    exit 1
fi

# Show summary
echo ""
echo "=== SUMMARY ==="
git log --oneline origin/main..HEAD 2>/dev/null || git log --oneline HEAD~4..HEAD
echo ""
echo "=== STATS ==="
git diff --shortstat HEAD~4..HEAD
echo ""
echo -e "${GREEN}Ready to create PR!${NC}"
