/* extract dn list from ldif */

#include <stdio.h>
#include <string.h>

#define MAX_LINE 80

main(argv,argc)
char **argv;
int argc;
{
   char line[MAX_LINE+1];
   int dn=0;

   while (fgets(line,MAX_LINE,stdin))
      {
      *(strrchr(line,'\n'))='\0';

      if (dn==1)
         {
         if (*line!=' ')
            {
            printf("\n");
            dn=0;
            }
         else
            printf("%s",line+1); 
         }

      if (!strncmp(line,"dn:",3))
         {
         printf("%s",line+4); 
         dn=1;
         }

      }
}
