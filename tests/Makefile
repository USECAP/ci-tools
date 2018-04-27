all: clean hardcoded_passwords zero_malloc fuzzme

hardcoded_passwords:
	$(CC) hardcoded_passwords.c -lcrypt -o $@.so

zero_malloc:
	$(CC) -c zero_malloc.c -o $@.o

fuzzme:
	$(CC) -c fuzzme.c -o $@.o

clean:
	rm -f *.o *.so
	rm -rf scan-build-*
	rm -f fuzzing/*.o
	find ci-fuzzing-targets -executable -type f -exec rm {} \;
	rm -rf ci-fuzzing-targets/crash-*
