#!/bin/bash

# Cuebert Feedback Push Script
# Platform: macOS + Cursor.app (see Issue I-4 in cuebert-gaming-system plan).
# Moves staged feedback files to a dedicated branch and pushes to remote
#
# Usage: npm run cuebert:push-feedback
#        or: ./scripts/push-feedback.sh

set -e

STAGING_DIR=".cuebert/feedback/staging"
SENT_DIR=".cuebert/feedback/sent"
FEEDBACK_BRANCH="cuebert-feedback"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "🔄 Cuebert Feedback Push"
echo "===================="

# Check if staging directory exists and has files
if [ ! -d "$STAGING_DIR" ]; then
    echo -e "${YELLOW}⚠ No staging directory found at $STAGING_DIR${NC}"
    exit 0
fi

FILES=$(ls -A "$STAGING_DIR" 2>/dev/null | grep -E "^FEEDBACK-.*\.md$" || true)

if [ -z "$FILES" ]; then
    echo -e "${YELLOW}⚠ No feedback files found in $STAGING_DIR${NC}"
    exit 0
fi

# Count files
FILE_COUNT=$(echo "$FILES" | wc -l | tr -d ' ')
echo "Found $FILE_COUNT feedback file(s) to push"
echo ""

# List files
echo "Files to push:"
for f in $FILES; do
    echo "  - $f"
done
echo ""

# Step 1: Stash current work
echo "📦 Stashing current work..."
git stash push -m "Auto-stash for Cuebert Feedback push" --quiet 2>/dev/null || true

# Step 2: Fetch and checkout feedback branch
echo "🔀 Switching to $FEEDBACK_BRANCH branch..."
git fetch origin 2>/dev/null || true

if git show-ref --verify --quiet "refs/heads/$FEEDBACK_BRANCH"; then
    git checkout "$FEEDBACK_BRANCH" --quiet
elif git show-ref --verify --quiet "refs/remotes/origin/$FEEDBACK_BRANCH"; then
    git checkout -b "$FEEDBACK_BRANCH" "origin/$FEEDBACK_BRANCH" --quiet
else
    git checkout -b "$FEEDBACK_BRANCH" --quiet
    echo "  Created new branch: $FEEDBACK_BRANCH"
fi

# Step 3: Create inbox directory and move files
echo "📁 Moving feedback files..."
mkdir -p "feedback/inbox"

for f in $FILES; do
    cp "$STAGING_DIR/$f" "feedback/inbox/"
    echo "  Copied: $f"
done

# Step 4: Commit and push
echo "📤 Committing and pushing..."
git add "feedback/inbox/"
git commit -m "Cuebert Batch: Feedback from user $(date +%Y-%m-%d)" --quiet

if git push origin "$FEEDBACK_BRANCH" 2>/dev/null; then
    echo -e "${GREEN}✅ Pushed to origin/$FEEDBACK_BRANCH${NC}"
else
    echo -e "${RED}❌ Push failed. Check remote access.${NC}"
    # Still continue to cleanup
fi

# Step 5: Return to previous branch
echo "🔙 Returning to previous branch..."
git checkout - --quiet

# Step 6: Move files to sent directory
echo "📂 Archiving sent files..."
mkdir -p "$SENT_DIR"
for f in $FILES; do
    mv "$STAGING_DIR/$f" "$SENT_DIR/"
done

# Step 7: Pop stash
echo "📦 Restoring stashed work..."
git stash pop --quiet 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Complete! $FILE_COUNT feedback file(s) pushed.${NC}"
echo ""
echo "Feedback is now on branch: $FEEDBACK_BRANCH"
echo "Cuebert maintainers will review your suggestions."
echo ""
