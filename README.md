# Photo-sorter
Moves all photos from a source directory to a destination sorted by date
Proposed changes from Anluren:
   1. add textbox on the main windows to display current status:
        . number of files processed in source directory
        . number of files copied, which is number in first bullet minus 
          duplicates
   2. add options dialog, so the program can:
        . simply the logic of comparing identical picture, so it runs faster
          when dealing with very large number of files and slow links (network).
   3. picture without date taken should be put into "unsorted" subdirectory
   4. need to test raw file (.cr2)
 
