python$target:::line
/basename(copyinstr(arg0)) == "program.py"/
{
        printf("%d\t%*s:", timestamp, 15, probename);
        printf("%s:%s:%d\n", basename(copyinstr(arg0)), copyinstr(arg1), arg2);
}
